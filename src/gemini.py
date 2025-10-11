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
    # Fallback for environments without API key (useful for DRY_RUN demos/tests)
    if not config.GOOGLE_API_KEY:
        return (
            "[DRY_RUN] AI content would be generated here. "
            "Set GOOGLE_API_KEY to enable real generation.\n\nPrompt preview: "
            + (prompt[:240] + ("…" if len(prompt) > 240 else ""))
        )

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
        
        # Safe extraction: handle multi-part responses
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                # Concatenate all text parts
                text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text')]
                return "".join(text_parts).strip()
        
        # Fallback: try simple accessor (for backward compatibility)
        try:
            return response.text.strip()
        except:
            pass
        
        # Last resort
        raise ValueError("Gemini response contained no usable text content")
        
    except Exception as e:
        print(f"Error generating text with Gemini: {e}")
        raise
