# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# A simple configuration setup to be expanded later
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./linkedin_agent.db")
