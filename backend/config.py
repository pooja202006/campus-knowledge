import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "campus_knowledge_db")
PORT = int(os.getenv("PORT", 8000))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.35))
EMBEDDING_DIMENSION = 768

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "campus-nexus-secret-key")
STUDENT_USERNAME = os.getenv("STUDENT_USERNAME", "student")
STUDENT_PASSWORD = os.getenv("STUDENT_PASSWORD", "campus123")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "campusadmin")
