import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "campus_knowledge_db")
PORT = int(os.getenv("PORT", 8000))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.35))
EMBEDDING_DIMENSION = 768
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
CORS_ORIGINS = [
	"http://localhost:3000",
	"http://localhost:5173",
	"http://127.0.0.1:3000",
	"http://127.0.0.1:5173",
]
CORS_ORIGINS.extend(
	origin.strip().rstrip("/")
	for origin in FRONTEND_URL.split(",")
	if origin.strip()
)

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "campus-nexus-secret-key")
STUDENT_USERNAME = os.getenv("STUDENT_USERNAME", "student")
STUDENT_PASSWORD = os.getenv("STUDENT_PASSWORD", "campus123")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "campusadmin")

if APP_ENV == "production":
	required_values = {
		"MONGODB_URI": MONGODB_URI,
		"GEMINI_API_KEY": GEMINI_API_KEY,
		"APP_SECRET_KEY": os.getenv("APP_SECRET_KEY", ""),
		"STUDENT_PASSWORD": os.getenv("STUDENT_PASSWORD", ""),
		"ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", ""),
	}
	missing_values = [name for name, value in required_values.items() if not value.strip()]
	if missing_values:
		raise RuntimeError(f"Missing required production environment variables: {', '.join(missing_values)}")
	if len(APP_SECRET_KEY) < 32 or APP_SECRET_KEY == "campus-nexus-secret-key":
		raise RuntimeError("APP_SECRET_KEY must be a unique value of at least 32 characters in production.")
	if (
		len(STUDENT_PASSWORD) < 12
		or len(ADMIN_PASSWORD) < 12
		or STUDENT_PASSWORD == "campus123"
		or ADMIN_PASSWORD == "campusadmin"
		or STUDENT_PASSWORD == ADMIN_PASSWORD
	):
		raise RuntimeError("Production student and admin passwords must be distinct and at least 12 characters long.")
