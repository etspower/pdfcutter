import os
from dotenv import load_dotenv
from src.constants import DEFAULT_SYSTEM_PROMPT

load_dotenv()

class Config:
    API_BASE_URL = os.getenv("PDFCUTTER_API_BASE_URL", "https://api.openai.com/v1")
    API_KEY = os.getenv("PDFCUTTER_API_KEY", "")
    MODEL = os.getenv("PDFCUTTER_MODEL", "gpt-4o")
    TIMEOUT = int(os.getenv("PDFCUTTER_TIMEOUT", "60"))
    SYSTEM_PROMPT = os.getenv("PDFCUTTER_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
