import hashlib
import json
import random
import logging
from google import genai
from google.genai import types
from backend.config import GEMINI_API_KEY, EMBEDDING_DIMENSION

logger = logging.getLogger("gemini")

class GeminiService:
    def __init__(self):
        self.client = None
        self.has_api_key = False
        if GEMINI_API_KEY and GEMINI_API_KEY.strip() != "":
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                self.has_api_key = True
                logger.info("Gemini API Client initialized successfully.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client with key: {e}")
        else:
            logger.info("GEMINI_API_KEY not set. Using smart fallback embeddings and synthesis.")

    def generate_embedding(self, text: str) -> list:
        """Generates 768-dim vector embedding using Gemini text-embedding-004."""
        if self.has_api_key and self.client:
            try:
                response = self.client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=text,
                    config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSION),
                )
                embeddings = getattr(response, "embeddings", None)
                if embeddings and embeddings[0].values:
                    return list(embeddings[0].values)
            except Exception as e:
                logger.warning(f"Gemini embedding API error: {e}. Falling back to hash vector.")
        
        # Stable fallback vectors keep offline ingestion comparable across processes.
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        generator = random.Random(seed)
        vec = [generator.uniform(-0.1, 0.1) for _ in range(EMBEDDING_DIMENSION)]
        # Normalize vector
        norm = sum(x*x for x in vec) ** 0.5
        return [x/norm for x in vec]

    def detect_language(self, text: str) -> str:
        """Detects if query is English, Tamil, or Tanglish."""
        tamil_range = range(0x0B80, 0x0BFF)
        has_tamil_char = any(ord(char) in tamil_range for char in text)
        if has_tamil_char:
            return "Tamil"
        
        tanglish_keywords = ["eppo", "engae", "enna", "paangada", "kaattungga", "aagum", "panlaam", "fees", "exam", "sem", "arrear"]
        lower_text = text.lower()
        if any(w in lower_text for w in tanglish_keywords):
            return "Tanglish"
        
        return "English"

    def synthesize_answer(self, query: str, context_chunks: list, language: str = "English") -> dict:
        """Synthesizes grounded answer using Gemini LLM."""
        if not context_chunks:
            return {
                "answer": "I couldn't find this information in the available campus documents.",
                "citations": [],
                "status": "i_dont_know"
            }

        # Build context text
        formatted_context = ""
        for idx, chunk in enumerate(context_chunks, 1):
            formatted_context += f"--- CHUNK {idx} ---\n"
            formatted_context += f"Document: {chunk.get('file_name', 'Unknown')}\n"
            formatted_context += f"Page Number: {chunk.get('page_number', 1)}\n"
            formatted_context += f"Section: {chunk.get('section', 'General')}\n"
            formatted_context += f"Content: {chunk.get('text', '')}\n\n"

        prompt = f"""You select evidence for Campus Nexus AI.
    Select only complete, relevant sentences copied EXACTLY from the supplied context that directly answer the question.
    Do not write, translate, paraphrase, combine, or add any words to the source sentences. The server will verify each sentence against the original retrieved text and add its citation.
    Ignore tables of contents and title lists when the question asks for details such as a challenge, problem, or deliverable; use the matching descriptive passage instead.
    Return JSON only in this shape: {{"points": ["exact source sentence", ...]}}.
    Return at most five distinct sentences, ordered by usefulness. If the context does not directly answer the question, return {{"points": []}}.

    QUESTION LANGUAGE: {language}

    CONTEXT:
    {formatted_context}

    QUESTION:
    {query}
    """

        if self.has_api_key and self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )
                payload = json.loads(response.text or "{}")
                points = payload.get("points", [])
                if not isinstance(points, list):
                    raise ValueError("Gemini response did not contain a points list.")
                points = [point.strip() for point in points if isinstance(point, str) and point.strip()][:5]
                return {
                    "points": points,
                    "status": "answered" if points else "i_dont_know",
                }
            except Exception as e:
                logger.warning(f"Gemini API error during synthesis: {e}. Utilizing fallback synthesis.")

        # Keep offline responses extractive too; citation metadata is attached by the verifier.
        top_chunk = context_chunks[0]
        return {
            "points": [top_chunk.get("text", "").strip()],
            "status": "answered" if top_chunk.get("text", "").strip() else "i_dont_know",
        }

gemini_service = GeminiService()
