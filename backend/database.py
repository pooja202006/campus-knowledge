import math
import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from backend.config import MONGODB_URI, DATABASE_NAME

logger = logging.getLogger("database")

class CampusDatabase:
    def __init__ (self):
        self.client = None
        self.db = None
        self.is_connected = False
        self.fallback_documents = []
        self.fallback_chunks = []
        self.fallback_logs = []
        self._connect()

    def _connect(self):
        if MONGODB_URI and MONGODB_URI.startswith("mongodb"):
            try:
                self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
                # Quick ping test
                self.client.admin.command('ping')
                self.db = self.client[DATABASE_NAME]
                self.is_connected = True
                self._ensure_indexes()
                logger.info(f"Connected to MongoDB Atlas: {DATABASE_NAME}")
            except Exception as e:
                logger.warning(f"MongoDB connection warning: {e}. Utilizing persistent local memory storage.")
                self.is_connected = False
        else:
            logger.info("MONGODB_URI not provided or invalid. Using local database storage.")
            self.is_connected = False

    def _ensure_indexes(self):
        if self.is_connected and self.db is not None:
            try:
                self.db.documents.create_index([("document_id", ASCENDING)], unique=True)
                self.db.chunks.create_index([("document_id", ASCENDING)])
                self.db.query_logs.create_index([("timestamp", ASCENDING)])
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    def save_document(self, doc_data: dict):
        if self.is_connected and self.db is not None:
            self.db.documents.update_one(
                {"document_id": doc_data["document_id"]},
                {"$set": doc_data},
                upsert=True
            )
        else:
            self.fallback_documents = [d for d in self.fallback_documents if d["document_id"] != doc_data["document_id"]]
            self.fallback_documents.append(doc_data)

    def save_chunks(self, chunks: list):
        if not chunks:
            return
        if self.is_connected and self.db is not None:
            doc_id = chunks[0]["document_id"]
            self.db.chunks.delete_many({"document_id": doc_id})
            self.db.chunks.insert_many(chunks)
        else:
            doc_id = chunks[0]["document_id"]
            self.fallback_chunks = [c for c in self.fallback_chunks if c.get("document_id") != doc_id]
            self.fallback_chunks.extend(chunks)

    def get_documents(self):
        if self.is_connected and self.db is not None:
            docs = list(self.db.documents.find({}, {"_id": 0}))
            return docs
        return self.fallback_documents

    def get_document_by_filename(self, file_name: str):
        if self.is_connected and self.db is not None:
            return self.db.documents.find_one({"file_name": file_name}, {"_id": 0})
        return next((doc for doc in self.fallback_documents if doc.get("file_name") == file_name), None)

    def get_all_chunks(self):
        if self.is_connected and self.db is not None:
            return list(self.db.chunks.find({}, {"_id": 0}))
        return self.fallback_chunks

    def vector_search(self, query_embedding: list, query_text: str = "", top_k: int = 5):
        """Performs hybrid vector & keyword similarity search over stored chunks."""
        chunks = self.get_all_chunks()
        if not chunks:
            return []

        def cosine_similarity(v1, v2):
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            mag1 = math.sqrt(sum(a * a for a in v1))
            mag2 = math.sqrt(sum(b * b for b in v2))
            if mag1 == 0 or mag2 == 0:
                return 0.0
            return dot / (mag1 * mag2)

        def keyword_overlap_score(q_str, c_str):
            if not q_str or not c_str:
                return 0.0
            q_words = set(w.lower() for w in q_str.split() if len(w) > 2)
            c_words = set(w.lower() for w in c_str.split() if len(w) > 2)
            if not q_words:
                return 0.0
            overlap = q_words.intersection(c_words)
            return len(overlap) / len(q_words)

        scored_chunks = []
        for chunk in chunks:
            emb = chunk.get("embedding", [])
            v_score = cosine_similarity(query_embedding, emb)
            k_score = keyword_overlap_score(query_text, chunk.get("text", ""))
            
            # Hybrid combined score
            combined_score = max(v_score, k_score * 0.95) if k_score > 0 else v_score
            
            chunk_copy = dict(chunk)
            chunk_copy["similarity_score"] = round(combined_score, 4)
            scored_chunks.append(chunk_copy)

        scored_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_chunks[:top_k]

    def log_query(self, log_entry: dict):
        log_entry["timestamp"] = datetime.utcnow().isoformat()
        if self.is_connected and self.db is not None:
            self.db.query_logs.insert_one(log_entry)
        else:
            self.fallback_logs.append(log_entry)

    def get_analytics(self):
        if self.is_connected and self.db is not None:
            logs = list(self.db.query_logs.find({}, {"_id": 0}))
        else:
            logs = self.fallback_logs

        total_queries = len(logs)
        answered_count = sum(1 for l in logs if l.get("status") == "answered")
        idk_count = sum(1 for l in logs if l.get("status") == "i_dont_know")

        # Language distribution
        langs = {}
        for l in logs:
            lang = l.get("language", "English")
            langs[lang] = langs.get(lang, 0) + 1

        # Most asked queries
        query_counts = {}
        for l in logs:
            q = l.get("query", "").strip()
            if q:
                query_counts[q] = query_counts.get(q, 0) + 1
        sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Recent unanswered queries
        unanswered = [l.get("query") for l in logs if l.get("status") == "i_dont_know"][-5:]

        return {
            "total_queries": total_queries,
            "answered_count": answered_count,
            "idk_count": idk_count,
            "language_distribution": langs,
            "top_queries": [{"query": q, "count": c} for q, c in sorted_queries],
            "unanswered_queries": unanswered,
            "total_documents": len(self.get_documents())
        }

db_instance = CampusDatabase()
