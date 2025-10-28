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
    max_tokens: Optional[int] = None,
    _attempt: int = 0,
) -> str:
    """Generate text using Gemini with robust error handling.

    This function tries multiple extraction strategies and, on failure
    (including safety blocks), returns a safe fallback string instead
    of raising so callers can continue in degraded mode.
    """
    if not config.GOOGLE_API_KEY:
        return (
            "[DRY_RUN] AI content would be generated here. "
            "Set GOOGLE_API_KEY to enable real generation.\n\nPrompt preview: "
            + (prompt[:240] + ("\u2026" if len(prompt) > 240 else ""))
        )

    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        retry_cap = max(256, min(config.GEMINI_MAX_OUTPUT_TOKENS, 8192))
        retry_step = max(128, min(config.GEMINI_RETRY_STEP, retry_cap))
        effective_max = retry_cap if max_tokens is None else min(max_tokens, retry_cap)

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=effective_max,
        )

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        # Method 1: direct response.text
        try:
            text = getattr(response, "text", None)
            if text and isinstance(text, str) and text.strip():
                result = text.strip()
                print(f"Method 1 (response.text) success: extracted {len(result)} chars")
                return result
        except Exception as e:
            print(f"Method 1 (response.text) failed: {e}")

        # Method 2: candidates -> content.parts
        try:
            candidate = response.candidates[0] if getattr(response, "candidates", None) else None
            if candidate is not None:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts:
                    text_parts = []
                    for part in parts:
                        text_value = getattr(part, "text", None) if part is not None else None
                        if text_value and str(text_value).strip():
                            text_parts.append(str(text_value))
                    if text_parts:
                        result = "".join(text_parts).strip()
                        if result:
                            print(f"Method 2 (parts) success: extracted {len(result)} chars")
                            return result
        except Exception as e:
            print(f"Method 2 (parts) failed: {e}")

        # Method 3: try low-level _result structure
        try:
            if hasattr(response, "_result"):
                result_obj = response._result
                if hasattr(result_obj, "candidates") and result_obj.candidates:
                    candidate = result_obj.candidates[0]
                    if hasattr(candidate, "content") and candidate.content:
                        if hasattr(candidate.content, "parts") and candidate.content.parts:
                            first_part = candidate.content.parts[0]
                            if hasattr(first_part, "text"):
                                result = first_part.text.strip()
                                if result:
                                    print(f"Method 3 (_result) success: extracted {len(result)} chars")
                                    return result
        except Exception as e:
            print(f"Method 3 (_result) failed: {e}")

        # Check for explicit safety blocks
        try:
            if hasattr(response, "prompt_feedback"):
                feedback = response.prompt_feedback
                if hasattr(feedback, "block_reason") and getattr(feedback, "block_reason"):
                    print(f"Gemini response blocked: {getattr(feedback, 'block_reason')}")
                    return (
                        "[AI üretimi başarısız veya engellendi] Özet üretilemedi. "
                        "Lütfen GOOGLE_API_KEY veya model durumunu kontrol edin."
                    )
        except Exception as e:
            print(f"Block reason check: {e}")

        # Analyze finish reason for retry possibility
        finish_reason_value = None
        finish_reason_label = ""
        try:
            if getattr(response, "candidates", None):
                cand = response.candidates[0]
                fr = getattr(cand, "finish_reason", None)
                if fr is not None:
                    finish_reason_value = getattr(fr, "value", fr)
                    finish_reason_label = getattr(fr, "name", "") or (
                        FINISH_REASON_LABELS.get(finish_reason_value) if isinstance(finish_reason_value, int) else str(fr)
                    )
        except Exception:
            pass

        error_details = []
        try:
            if getattr(response, "candidates", None) is not None:
                error_details.append(f"candidates count: {len(response.candidates) if response.candidates else 0}")
            if hasattr(response, "prompt_feedback"):
                error_details.append(f"prompt_feedback: {response.prompt_feedback}")
            if finish_reason_label:
                error_details.append(f"finish_reason: {finish_reason_label}")
            elif finish_reason_value is not None:
                error_details.append(f"finish_reason: {finish_reason_value}")
        except Exception:
            pass

        if (
            (finish_reason_label == "MAX_TOKENS" or finish_reason_value == 2)
            and _attempt < 3
            and effective_max < retry_cap
        ):
            new_max_tokens = min(effective_max + retry_step, retry_cap)
            if new_max_tokens > effective_max:
                print(
                    "Gemini response truncated (finish_reason=MAX_TOKENS). "
                    f"Retrying with max_tokens={new_max_tokens} (attempt {_attempt + 1})."
                )
                return generate_text(
                    prompt,
                    temperature=temperature,
                    max_tokens=new_max_tokens,
                    _attempt=_attempt + 1,
                )

        # If nothing worked, return a helpful fallback instead of raising
        print(f"Gemini produced no usable text. Details: {', '.join(error_details) if error_details else 'none'}")
        return (
            "[AI üretimi başarısız veya engellendi] Özet üretilemedi. "
            "Lütfen GOOGLE_API_KEY veya model durumunu kontrol edin."
        )

    except Exception as e:
        print(f"Gemini API hatası: {e}")
        return (
            "[AI üretimi hatası] Kısa özet üretilemedi. Hata: " + str(e)
        )
