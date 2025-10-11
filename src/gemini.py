"""Google Gemini integration."""
import google.generativeai as genai
from typing import Optional
from .config import config


FINISH_REASON_LABELS = {
    0: "FINISH_REASON_UNSPECIFIED",
    1: "STOP",
    2: "MAX_TOKENS",
    3: "SAFETY",
    4: "RECITATION",
    5: "OTHER",
}


def init_gemini():
    """Initialize Gemini API."""
    if config.GOOGLE_API_KEY:
        genai.configure(api_key=config.GOOGLE_API_KEY)
        print("Gemini API initialized")
    else:
        print("Warning: GOOGLE_API_KEY not set")


def generate_text(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    _attempt: int = 0,
    _force_concise: bool = False,
) -> str:
    """Generate text using Gemini with robust error handling."""
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
        
        # Add safety settings to prevent blocking
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            },
        ]
        
        effective_prompt = prompt
        if _force_concise:
            effective_prompt = (
                prompt
                + "\n\nIMPORTANT: Keep the final response under 180 words. Be direct, avoid repetition, and do not add disclaimers."
            )
            print("Gemini retry enforcing concise response (<=180 words).")

        response = model.generate_content(
            effective_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        candidate = response.candidates[0] if getattr(response, "candidates", None) else None
        finish_reason_value = None
        finish_reason_label = ""
        if candidate is not None:
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason is not None:
                finish_reason_value = getattr(finish_reason, "value", finish_reason)
                finish_reason_label = getattr(finish_reason, "name", "")
                if not finish_reason_label and isinstance(finish_reason_value, int):
                    finish_reason_label = FINISH_REASON_LABELS.get(
                        finish_reason_value, str(finish_reason_value)
                    )
                elif not finish_reason_label:
                    finish_reason_label = str(finish_reason)
        
        # Method 1: Try simple .text accessor (recommended by Gemini docs, works for most cases)
        try:
            text = response.text  # This may raise exception for non-simple responses
            if text:
                result = text.strip()
                if result:
                    print(f"Method 1 (response.text) success: extracted {len(result)} chars")
                    return result
        except Exception as e:
            print(f"Method 1 (response.text) failed: {e}")
        
        # Method 2: Try candidates[0].content.parts (for multi-part responses)
        try:
            if candidate is not None:
                content = getattr(candidate, 'content', None)
                parts = getattr(content, 'parts', None) if content else None
                if parts:
                    text_parts = []
                    for part in parts:
                        if hasattr(part, 'text'):
                            text_value = getattr(part, 'text', '')
                            if text_value and str(text_value).strip():
                                text_parts.append(str(text_value))
                    if text_parts:
                        result = "".join(text_parts).strip()
                        if result:
                            print(f"Method 2 (parts) success: extracted {len(result)} chars")
                            return result
        except Exception as e:
            print(f"Method 2 (parts) failed: {e}")
        
        # Method 3: Try _result.candidates[0].content.parts[0].text (internal structure)
        try:
            if hasattr(response, '_result'):
                result_obj = response._result
                if hasattr(result_obj, 'candidates') and result_obj.candidates:
                    candidate = result_obj.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            if hasattr(candidate.content.parts[0], 'text'):
                                result = candidate.content.parts[0].text.strip()
                                if result:
                                    print(f"Method 3 (_result) success: extracted {len(result)} chars")
                                    return result
        except Exception as e:
            print(f"Method 3 (_result) failed: {e}")
        
        # Method 4: Check if response was blocked
        try:
            if hasattr(response, 'prompt_feedback'):
                feedback = response.prompt_feedback
                if hasattr(feedback, 'block_reason'):
                    raise ValueError(f"Gemini yanıtı engellendi: {feedback.block_reason}")
        except Exception as e:
            print(f"Block reason check: {e}")
        
        # Last resort: detailed error
        error_details = []
        if hasattr(response, 'candidates'):
            error_details.append(
                f"candidates count: {len(response.candidates) if response.candidates else 0}"
            )
        if hasattr(response, 'prompt_feedback'):
            error_details.append(f"prompt_feedback: {response.prompt_feedback}")
        if finish_reason_label:
            error_details.append(f"finish_reason: {finish_reason_label}")
        elif finish_reason_value is not None:
            error_details.append(f"finish_reason: {finish_reason_value}")

        # Retry automatically if response was truncated
        if (
            (finish_reason_label == "MAX_TOKENS" or finish_reason_value == 2)
            and _attempt < 3
            and max_tokens < 3072
        ):
            new_max_tokens = min(max_tokens + 600, 3072)
            next_force_concise = _force_concise or (_attempt >= 1)
            if new_max_tokens > max_tokens:
                print(
                    "Gemini response truncated (finish_reason=MAX_TOKENS). "
                    f"Retrying with max_tokens={new_max_tokens} (attempt {_attempt + 1})."
                )
                return generate_text(
                    prompt,
                    temperature=temperature,
                    max_tokens=new_max_tokens,
                    _attempt=_attempt + 1,
                    _force_concise=next_force_concise,
                )
        
        raise ValueError(
            f"Gemini yanıtı kullanılabilir metin içermiyor. "
            f"Detaylar: {', '.join(error_details) if error_details else 'bilinmiyor'}. "
            f"Lütfen promptu kontrol edin veya API durumunu inceleyin."
        )
        
    except ValueError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch all other errors
        print(f"Gemini API hatası: {e}")
        raise ValueError(f"Gemini API ile iletişim hatası: {str(e)}")
