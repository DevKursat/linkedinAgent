"""Google Gemini integration."""
import google.generativeai as genai
from typing import Optional
from .config import config


def init_gemini():
    """Initialize Gemini API."""
    if config.GOOGLE_API_KEY:
        genai.configure(api_key=config.GOOGLE_API_KEY)
        print("Gemini API initialized")
    else:
        print("Warning: GOOGLE_API_KEY not set")


def generate_text(prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
    """Generate text using Gemini."""
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text.strip()
    except Exception as e:
        print(f"Error generating text with Gemini: {e}")
        raise
