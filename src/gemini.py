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
    """Generate text using Gemini with robust error handling."""
    if not config.GOOGLE_API_KEY:
        return (
            "[DRY_RUN] AI content would be generated here. "
            "Set GOOGLE_API_KEY to enable real generation.\n\nPrompt preview: "
            + (prompt[:240] + ("…" if len(prompt) > 240 else ""))
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
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
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

        try:
            text = response.text
            if text:
                result = text.strip()
                if result:
                    print(f"Method 1 (response.text) success: extracted {len(result)} chars")
                    return result
        except Exception as e:
            print(f"Method 1 (response.text) failed: {e}")

        try:
            if candidate is not None:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts:
                    text_parts = []
                    for part in parts:
                        if hasattr(part, "text"):
                            text_value = getattr(part, "text", "")
                            if text_value and str(text_value).strip():
                                text_parts.append(str(text_value))
                    if text_parts:
                        result = "".join(text_parts).strip()
                        if result:
                            print(f"Method 2 (parts) success: extracted {len(result)} chars")
                            return result
        except Exception as e:
            print(f"Method 2 (parts) failed: {e}")

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

        try:
            if hasattr(response, "prompt_feedback"):
                feedback = response.prompt_feedback
                if hasattr(feedback, "block_reason"):
                    raise ValueError(f"Gemini yanıtı engellendi: {feedback.block_reason}")
        except Exception as e:
            print(f"Block reason check: {e}")

        error_details = []
        if hasattr(response, "candidates"):
            count = len(response.candidates) if response.candidates else 0
            error_details.append(f"candidates count: {count}")
        if hasattr(response, "prompt_feedback"):
            error_details.append(f"prompt_feedback: {response.prompt_feedback}")
        if finish_reason_label:
            error_details.append(f"finish_reason: {finish_reason_label}")
        elif finish_reason_value is not None:
            error_details.append(f"finish_reason: {finish_reason_value}")

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

        raise ValueError(
            f"Gemini yanıtı kullanılabilir metin içermiyor. "
            f"Detaylar: {', '.join(error_details) if error_details else 'bilinmiyor'}. "
            f"Lütfen promptu kontrol edin veya API durumunu inceleyin."
        )

    except ValueError:
        raise
    except Exception as e:
        print(f"Gemini API hatası: {e}")
        raise ValueError(f"Gemini API ile iletişim hatası: {str(e)}")
