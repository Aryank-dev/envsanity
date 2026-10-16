import os

api_key = os.getenv("API_KEY")
db = os.environ["DATABASE_URL"]
port = os.environ.get("PORT", "8080")
debug = os.getenv("DEBUG")
