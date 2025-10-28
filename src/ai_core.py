# src/ai_core.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
from .persona import get_persona_prompt

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API
api_key = os.getenv("GEMINI_API_KEY")
model = None
if not api_key:
    print("⚠️ WARNING: GEMINI_API_KEY not found in .env file. AI features will be disabled.")
else:
    try:
        genai.configure(api_key=api_key)
        # Initialize the model
        model = genai.GenerativeModel('gemini-pro')
        print("✅ Gemini AI Model initialized successfully.")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize Gemini AI Model: {e}")


def generate_text(task_prompt: str) -> str:
    """
    Generates text using the Gemini model based on the persona and a specific task.

    Args:
        task_prompt: The specific instruction for the task (e.g., "Write a comment for this post...").

    Returns:
        The generated text as a string.
    """
    if not model:
        print("❌ ERROR: Gemini model is not initialized. Cannot generate text.")
        return "[AI functionality disabled. Please check GEMINI_API_KEY]"

    try:
        # Combine the main persona prompt with the specific task prompt
        full_prompt = get_persona_prompt() + "\n\n--- TASK ---\n\n" + task_prompt

        # Generate content
        response = model.generate_content(full_prompt)

        # Clean up the response text
        generated_text = response.text.strip()

        return generated_text
    except Exception as e:
        print(f"An error occurred while generating text: {e}")
        return "" # Return empty string on failure

if __name__ == '__main__':
    # A simple test to verify the functionality
    print("--- Testing AI Core Module ---")
    test_task = "Write a short, witty comment in Turkish for a LinkedIn post about the challenges of remote work."
    generated_comment = generate_text(test_task)

    print(f"Task: {test_task}")
    print(f"Generated Comment: {generated_comment}")
