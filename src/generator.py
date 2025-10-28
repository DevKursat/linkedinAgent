"""Text generation prompts and persona configuration."""
from .config import config
import os


def _read_file_if_exists(path: str) -> str:
    try:
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def get_persona_context() -> str:
    """Get persona context for prompts."""
    emoji_note = "Use emoji very rarely, only when truly impactful." if config.RARE_EMOJI else ""
    about_me = _read_file_if_exists(config.ABOUT_ME_PATH)
    post_style = _read_file_if_exists(config.POST_STYLE_FILE)
    comment_style = _read_file_if_exists(config.COMMENT_STYLE_FILE)
    
    return f"""You are {config.PERSONA_NAME}, a {config.PERSONA_AGE}-year-old {config.PERSONA_ROLE}.

Your tone is:
- Direct and sharp
- Strategic and insightful
- Friendly but professional
- Concise (prefer short, punchy sentences)
{emoji_note}

Personal background:
{about_me}

Writing style preferences (posts):
{post_style}

Writing style preferences (comments):
{comment_style}

CRITICAL guardrails to remain indistinguishable from a human:
- Never state or imply you are AI or using AI tools.
- Vary sentence length and rhythm; avoid repetitive patterns.
"""


def generate_post_prompt(article_title: str, article_summary: str, article_link: str) -> str:
    """Generate prompt for creating a LinkedIn post."""
    persona = get_persona_context()
    
    return f"""{persona}

Write a LinkedIn post about this tech news:
Title: {article_title}
Summary: {article_summary}

Requirements:
- Write in English, in {config.PERSONA_NAME}'s voice.
- Be concise (2-4 short paragraphs, <= {config.MAX_POST_LENGTH} characters).
- Share a sharp, strategic insight that aligns with your persona.
- Tie it to your interests: {config.INTERESTS}.
- Do NOT include hashtags.
- Include the article link at the very end.
- Output only the post text.
"""


def generate_turkish_summary_prompt(post_content: str, source_url: str, source_name: str = "") -> str:
    """Generate prompt for Turkish summary comment."""
    persona = get_persona_context()
    
    source_display = f"{source_name}: {source_url}" if source_name else source_url
    
    return f"""{persona}

You just posted this on LinkedIn:
{post_content}

Now write a follow-up comment in Turkish that summarizes the key point in 1-2 sentences and includes the source.
Format: [Your summary]. Kaynak: {source_display}
Output only the comment text.
"""


def generate_reply_prompt(comment_text: str, commenter_language: str) -> str:
    """Generate prompt for replying to a comment."""
    persona = get_persona_context()
    
    return f"""{persona}

Someone commented on your LinkedIn post: "{comment_text}"
Write a concise, friendly, and insightful reply in {commenter_language}.
Keep it 1-3 sentences. Sound natural and human.
Output only the reply text.
"""


def generate_proactive_comment_prompt(post_content: str, context: str) -> str:
    """Generate prompt for proactive comment on others' posts."""
    persona = get_persona_context()

    goal = "add a sharp, insightful observation."
    if "LinkedIn Target" in context:
        goal = "ask a thought-provoking question or offer a respectful counter-point to deepen the discussion."
    elif "TechCrunch" in context or "Y Combinator" in context:
        goal = "tie this news to a broader industry trend and offer a specific, non-obvious prediction."

    return f"""{persona}

You are commenting on a LinkedIn post. Your goal is to {goal}
Post Content: "{post_content}"
Context: {context}

Your comment must:
- Be in English, in {config.PERSONA_NAME}'s voice.
- Be concise (2-3 powerful sentences).
- Demonstrate expertise as a {config.PERSONA_ROLE}.
- Spark conversation.
- NEVER reveal you are an AI.
- Output only the comment text.
"""


def generate_refine_post_prompt(draft_text: str, language: str = "English") -> str:
    """Generate a prompt to refine/improve a user's draft post."""
    persona = get_persona_context()
    return f"""{persona}

Revise this LinkedIn post draft. Keep the author's voice, improve clarity, and align with interests: {config.INTERESTS}.
Draft: "{draft_text}"
Constraints: Concise (<= {config.MAX_POST_LENGTH} chars), punchy opening, no boilerplate.
Language: {language}.
Output only the revised post text.
"""


def generate_invite_message(person_name: str = "") -> str:
    """Generate a short, personalized invite message."""
    persona = get_persona_context()
    name_part = f"{person_name}, " if person_name else ""
    return f"{persona}\n\nWrite a concise (1-2 sentence) LinkedIn connection message to {name_part}that explains why you'd like to connect, relevant to your role and interests: {config.INTERESTS}. Be friendly and professional. Output only the message text."
