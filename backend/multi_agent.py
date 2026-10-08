import time
import logging
import re
from backend.database import db_instance
from backend.gemini_client import gemini_service
from backend.config import SIMILARITY_THRESHOLD

logger = logging.getLogger("multi_agent")


def _normalize_evidence(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().casefold()


def _normalized_terms(text: str) -> set:
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for",
        "from", "how", "in", "is", "it", "of", "on", "or", "the", "to", "what",
        "when", "where", "which", "who", "why", "will", "with",
    }
    aliases = {
        "examination": "exam", "examinations": "exam", "exams": "exam",
        "commence": "start", "commences": "start", "commenced": "start", "begin": "start",
        "begins": "start", "conclude": "end", "concludes": "end", "concluded": "end",
        "finish": "end", "finishes": "end", "fees": "fee", "fare": "cost", "price": "cost",
        "costs": "cost", "deadline": "date", "dates": "date", "vacation": "holiday",
        "holidays": "holiday", "timings": "time", "timing": "time",
    }
    return {
        aliases.get(word, word[:-1] if word.endswith("s") and len(word) > 4 else word)
        for word in re.findall(r"[a-z0-9]+", text.casefold())
        if word not in stop_words
    }


def _verify_answer_points(candidate_points: list, retrieved_chunks: list, query: str) -> tuple:
    verified_points = []
    verified_citations = []
    seen_points = set()
    expanded_points = [
        sentence.strip()
        for candidate in candidate_points
        if isinstance(candidate, str)
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", candidate.strip())
        if sentence.strip()
    ]
    query_terms = _normalized_terms(query)
    minimum_overlap = min(2, len(query_terms))
    challenge_intent = "challenge" in query_terms
    for candidate in expanded_points:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        point = re.sub(r"\s+", " ", candidate).strip()
        normalized_point = _normalize_evidence(point)
        if not normalized_point or normalized_point in seen_points:
            continue
        if query_terms and len(query_terms.intersection(_normalized_terms(point))) < minimum_overlap:
            continue
        if challenge_intent and not {"challenge", "build", "deliverable"}.intersection(_normalized_terms(point)):
            continue

        source = next(
            (
                chunk for chunk in retrieved_chunks
                if normalized_point in _normalize_evidence(chunk.get("text", ""))
            ),
            None,
        )
        if not source:
            continue

        seen_points.add(normalized_point)
        verified_points.append(point)
        verified_citations.append({
            "file_name": source.get("file_name", "Campus Document"),
            "page_number": source.get("page_number", 1),
            "section": source.get("section", "General Information"),
            "snippet": point,
            "verified": True,
        })
    return verified_points, verified_citations

class MultiAgentCouncil:
    """
    5-Agent Collaborative Council for HN-AI-01:
    Agent 1: Ingestion Agent
    Agent 2: Retrieval Agent
    Agent 3: Answer Generation Agent
    Agent 4: Citation Verification Agent
    Agent 5: Quality/Confidence Guardrail Agent ("I Don't Know" trigger)
    """

    def process_student_query(self, user_query: str, language_override: str = "auto") -> dict:
        start_time = time.time()
        agent_logs = []

        # AGENT 1: Language & Intent Analysis
        detected_lang = gemini_service.detect_language(user_query) if language_override == "auto" else language_override
        agent_logs.append({
            "agent": "Agent 1 — Language & Intent Agent",
            "action": "Language Detection",
            "result": f"Detected language: {detected_lang}"
        })

        normalized_query = re.sub(r"\s+", " ", user_query.casefold()).strip(" .!?\t\n")
        simple_answer = None
        simple_status = "conversation"
        simple_citations = []

        if re.fullmatch(r"(hi|hello|hey|good morning|good afternoon|good evening)( there)?", normalized_query):
            simple_answer = "Hi! What would you like to know about campus? I can check the indexed documents for you."
        elif normalized_query in {"thanks", "thank you", "thanks a lot", "thank you so much"}:
            simple_answer = "You're welcome! What else would you like to look up?"
        elif normalized_query in {"help", "what can you do", "how can you help", "what can you help with"}:
            simple_answer = (
                "I can look up exam schedules, fees, courses, hostel and transport rules, scholarships, "
                "and the Hack Nexus brief in the indexed documents. Ask me a question or ask to see the document list."
            )
        elif (
            re.search(r"\b(documents?|pdfs?|files?)\b", normalized_query)
            and re.search(r"\b(available|list|have|show|uploaded|indexed|library)\b", normalized_query)
        ):
            documents = sorted(db_instance.get_documents(), key=lambda doc: doc.get("file_name", "").casefold())
            simple_status = "answered"
            if documents:
                simple_answer = "Here are the documents currently available in the campus library:\n\n" + "\n".join(
                    f"{index}. {doc.get('file_name', 'Campus Document')}"
                    for index, doc in enumerate(documents, start=1)
                )
                simple_citations = [
                    {
                        "file_name": doc.get("file_name", "Campus Document"),
                        "page_number": 1,
                        "section": "Document Library",
                        "snippet": doc.get("title") or doc.get("file_name", "Campus Document"),
                        "verified": True,
                    }
                    for doc in documents
                ]
            else:
                simple_answer = "I don't see any documents in the library yet. Ask a faculty member to add the campus PDFs and I'll check again."

        if simple_answer is not None:
            agent_logs.append({
                "agent": "Agent 1 — Language & Intent Agent",
                "action": "Friendly Conversation" if simple_status == "conversation" else "Document Library Lookup",
                "result": "Answered without semantic retrieval." if simple_status == "conversation" else f"Listed {len(simple_citations)} indexed documents."
            })
            latency = int((time.time() - start_time) * 1000)
            db_instance.log_query({
                "query": user_query,
                "language": detected_lang,
                "status": simple_status,
                "max_similarity_score": 0.0,
                "latency_ms": latency,
                "cited_documents": [cite["file_name"] for cite in simple_citations],
            })
            return {
                "answer": simple_answer,
                "citations": simple_citations,
                "status": simple_status,
                "language": detected_lang,
                "latency_ms": latency,
                "agent_logs": agent_logs,
            }

        # AGENT 2: Semantic Retrieval Agent
        query_vec = gemini_service.generate_embedding(user_query)
        retrieved_chunks = db_instance.vector_search(query_vec, query_text=user_query, top_k=4)
        
        agent_logs.append({
            "agent": "Agent 2 — Semantic Retrieval Agent",
            "action": "MongoDB Vector Search",
            "result": f"Retrieved {len(retrieved_chunks)} relevant chunks. Max score: {retrieved_chunks[0]['similarity_score'] if retrieved_chunks else 0.0}"
        })

        # AGENT 5: Quality & Confidence Guardrail Agent (Check score threshold)
        max_score = retrieved_chunks[0]['similarity_score'] if retrieved_chunks else 0.0
        if not retrieved_chunks or max_score < SIMILARITY_THRESHOLD:
            agent_logs.append({
                "agent": "Agent 5 — Quality & Confidence Guardrail Agent",
                "action": "Confidence Verification",
                "result": f"Similarity score ({max_score}) below threshold ({SIMILARITY_THRESHOLD}). Triggering 'I Don't Know' Fallback."
            })
            
            latency = int((time.time() - start_time) * 1000)
            idk_response = {
                "answer": "I couldn't find this information in the available campus documents.",
                "citations": [],
                "status": "i_dont_know",
                "language": detected_lang,
                "latency_ms": latency,
                "agent_logs": agent_logs
            }
            db_instance.log_query({
                "query": user_query,
                "language": detected_lang,
                "status": "i_dont_know",
                "max_similarity_score": max_score,
                "latency_ms": latency
            })
            return idk_response

        # AGENT 3: Answer Generation Agent (Gemini Grounded Synthesis)
        synthesis_result = gemini_service.synthesize_answer(user_query, retrieved_chunks, detected_lang)
        agent_logs.append({
            "agent": "Agent 3 — Answer Generation Agent",
            "action": "Gemini Grounded Synthesis",
            "result": f"Selected {len(synthesis_result.get('points', []))} source excerpts for verification."
        })

        if synthesis_result.get("status") == "i_dont_know":
            latency = int((time.time() - start_time) * 1000)
            synthesis_result["language"] = detected_lang
            synthesis_result["latency_ms"] = latency
            synthesis_result["agent_logs"] = agent_logs
            db_instance.log_query({
                "query": user_query,
                "language": detected_lang,
                "status": "i_dont_know",
                "max_similarity_score": max_score,
                "latency_ms": latency
            })
            return synthesis_result

        # AGENT 4: Verify every answer point against the retrieved source text.
        verified_points, verified_citations = _verify_answer_points(
            synthesis_result.get("points", []), retrieved_chunks, user_query
        )

        if not verified_points:
            source_sentences = [
                sentence.strip()
                for chunk in retrieved_chunks
                for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", chunk.get("text", ""))
                if sentence.strip()
            ]
            verified_points, verified_citations = _verify_answer_points(
                source_sentences, retrieved_chunks, user_query
            )
            if verified_points:
                agent_logs.append({
                    "agent": "Agent 3 — Answer Generation Agent",
                    "action": "Source-Only Recovery",
                    "result": f"Recovered {len(verified_points)} relevant points directly from retrieved document text."
                })

        if not verified_points:
            agent_logs.append({
                "agent": "Agent 4 — Citation Verification Agent",
                "action": "Exact Source Match",
                "result": "No generated answer point matched retrieved source text. Returning the no-answer response."
            })
            latency = int((time.time() - start_time) * 1000)
            db_instance.log_query({
                "query": user_query,
                "language": detected_lang,
                "status": "i_dont_know",
                "max_similarity_score": max_score,
                "latency_ms": latency,
            })
            return {
                "answer": "I couldn't find this information in the available campus documents.",
                "citations": [],
                "status": "i_dont_know",
                "language": detected_lang,
                "latency_ms": latency,
                "agent_logs": agent_logs,
            }

        agent_logs.append({
            "agent": "Agent 4 — Citation Verification Agent",
            "action": "Exact Source Match",
            "result": f"Verified {len(verified_points)} answer points against retrieved source text."
        })

        answer = "\n\n".join(
            f"{index}. {point}"
            for index, point in enumerate(verified_points, start=1)
        )

        latency = int((time.time() - start_time) * 1000)
        final_response = {
            "answer": answer,
            "citations": verified_citations,
            "status": "answered",
            "language": detected_lang,
            "latency_ms": latency,
            "agent_logs": agent_logs
        }

        db_instance.log_query({
            "query": user_query,
            "language": detected_lang,
            "status": "answered",
            "max_similarity_score": max_score,
            "latency_ms": latency,
            "cited_documents": [c["file_name"] for c in verified_citations]
        })

        return final_response

agent_council = MultiAgentCouncil()
