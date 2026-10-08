import os
import re
import uuid
import logging
from io import BytesIO
import pypdf
from backend.gemini_client import gemini_service
from backend.database import db_instance

logger = logging.getLogger("ingestion")

class PDFIngestionEngine:
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process_pdf_file(self, file_path: str, custom_filename: str = None) -> dict:
        filename = custom_filename or os.path.basename(file_path)
        with open(file_path, "rb") as pdf_file:
            return self.process_pdf_bytes(pdf_file.read(), custom_filename=filename)

    def process_pdf_bytes(self, pdf_bytes: bytes, custom_filename: str) -> dict:
        filename = custom_filename
        existing_document = db_instance.get_document_by_filename(filename)
        doc_id = existing_document.get("document_id") if existing_document else f"doc_{uuid.uuid4().hex[:8]}"

        try:
            reader = pypdf.PdfReader(BytesIO(pdf_bytes))
            num_pages = len(reader.pages)
            all_chunks = []

            for page_idx, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text() or ""
                clean_text = self._clean_text(raw_text)
                if not clean_text:
                    continue

                # Extract section headers if present
                sections = self._extract_sections(clean_text)
                
                # Create chunks
                page_chunks = self._chunk_text(clean_text)
                for chunk_idx, chunk_str in enumerate(page_chunks, start=1):
                    section_title = sections[0] if sections else "General Information"
                    embedding = gemini_service.generate_embedding(chunk_str)

                    chunk_obj = {
                        "chunk_id": f"{doc_id}_p{page_idx}_c{chunk_idx}",
                        "document_id": doc_id,
                        "file_name": filename,
                        "page_number": page_idx,
                        "section": section_title,
                        "text": chunk_str,
                        "embedding": embedding
                    }
                    all_chunks.append(chunk_obj)

            # Store in Database
            doc_data = {
                "document_id": doc_id,
                "file_name": filename,
                "title": filename.replace(".pdf", "").replace("_", " "),
                "uploaded_at": pypdf.__name__, # metadata timestamp
                "page_count": num_pages,
                "total_chunks": len(all_chunks),
                "status": "indexed"
            }

            db_instance.save_document(doc_data)
            db_instance.save_chunks(all_chunks)

            logger.info(f"Ingested '{filename}': {num_pages} pages, {len(all_chunks)} chunks.")
            return {
                "document_id": doc_id,
                "file_name": filename,
                "pages": num_pages,
                "chunks_count": len(all_chunks),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {e}")
            raise e

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_sections(self, text: str) -> list:
        matches = re.findall(r'(Section \d+:[^\.\n]+|Notice:[^\.\n]+|Chapter \d+:[^\.\n]+)', text, re.IGNORECASE)
        return [m.strip() for m in matches]

    def _chunk_text(self, text: str) -> list:
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start += (self.chunk_size - self.overlap)
        return chunks

ingestion_engine = PDFIngestionEngine()
