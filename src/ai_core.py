# src/ai_core.py
import google.generativeai as genai
from .config import settings
from .persona import get_persona_prompt
import time

# Configure the Gemini API using centralized config
api_key = settings.GEMINI_API_KEY
model = None
current_model_name = None
fallback_models = []

if not api_key:
    print("⚠️ WARNING: GEMINI_API_KEY not found in .env file. AI features will be disabled.")
else:
    try:
        genai.configure(api_key=api_key)
        # Initialize the primary model
        primary_model = settings.GEMINI_MODEL
        model = genai.GenerativeModel(primary_model)
        current_model_name = primary_model
        
        # Parse fallback models from comma-separated string
        if settings.GEMINI_FALLBACK_MODELS:
            fallback_models = [m.strip() for m in settings.GEMINI_FALLBACK_MODELS.split(',') if m.strip()]
        
        print(f"✅ Gemini AI Model initialized successfully: {current_model_name}")
        if fallback_models:
            print(f"   Fallback models available: {', '.join(fallback_models)}")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize Gemini AI Model: {e}")


def generate_text(task_prompt: str, retry_count: int = 0) -> str:
    """
    Generates text using the Gemini model based on the persona and a specific task.
    Automatically falls back to alternative models if quota is exhausted.

    Args:
        task_prompt: The specific instruction for the task (e.g., "Write a comment for this post...").
        retry_count: Internal counter for retry attempts (used for fallback).

    Returns:
        The generated text as a string, or None if generation fails.
    """
    global model, current_model_name
    
    if not model:
        print("⚠️ WARNING: Gemini model is not initialized. AI features are disabled.")
        return None

    try:
        # Combine the main persona prompt with the specific task prompt
        full_prompt = get_persona_prompt() + "\n\n--- TASK ---\n\n" + task_prompt

        # Generate content
        response = model.generate_content(full_prompt)

        # Clean up the response text
        generated_text = response.text.strip()
        
        if not generated_text:
            print("⚠️ WARNING: Generated text is empty.")
            return None

        return generated_text
        
    except Exception as e:
        error_str = str(e).lower()
        
        # Check if it's a quota/resource exhaustion error
        is_quota_error = any(keyword in error_str for keyword in [
            'quota', 'resource', 'exhausted', 'rate limit', 'too many requests', '429'
        ])
        
        if is_quota_error and retry_count < len(fallback_models):
            # Try fallback model
            fallback_model_name = fallback_models[retry_count]
            print(f"⚠️ Quota exhausted for {current_model_name}. Trying fallback model: {fallback_model_name}")
            
            try:
                model = genai.GenerativeModel(fallback_model_name)
                current_model_name = fallback_model_name
                print(f"✅ Switched to fallback model: {current_model_name}")
                
                # Add a small delay to avoid immediate rate limiting
                time.sleep(2)
                
                # Retry with the new model
                return generate_text(task_prompt, retry_count + 1)
                
            except Exception as fallback_error:
                print(f"❌ Fallback model {fallback_model_name} also failed: {fallback_error}")
                # Continue to try next fallback if available
                if retry_count + 1 < len(fallback_models):
                    return generate_text(task_prompt, retry_count + 1)
        
        print(f"⚠️ WARNING: AI content generation error: {e}")
        return None  # Return None on failure to indicate error

if __name__ == '__main__':
    # A simple test to verify the functionality
    print("--- Testing AI Core Module ---")
    test_task = "Write a short, witty comment in Turkish for a LinkedIn post about the challenges of remote work."
    generated_comment = generate_text(test_task)

    print(f"Task: {test_task}")
    print(f"Generated Comment: {generated_comment}")
