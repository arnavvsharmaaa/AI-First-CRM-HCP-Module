import json
import os
import re
from langchain_core.tools import tool
from langchain_groq import ChatGroq


def _strip_markdown_fences(text: str) -> str:
    """Remove any ```json ... ``` or ``` ... ``` wrappers from LLM output."""
    text = text.strip()
    # Remove opening fence (with optional language tag)
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    # Remove closing fence
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


@tool
async def suggest_followups(input: str) -> dict:
    """
    Suggests follow-up actions based on the current HCP interaction context.
    Call this when the user asks for next steps, follow-ups, or after logging an interaction.
    Input should be a summary of the current interaction including HCP name, topics discussed, and sentiment.
    Returns 3-5 concrete, actionable follow-up suggestions as a list.
    """
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )

    system_prompt = (
        "You are a pharmaceutical sales strategy assistant.\n"
        "Based on this HCP interaction summary, suggest 3 to 5 concrete follow-up actions.\n"
        "Keep each suggestion concise — under 12 words.\n"
        "Return ONLY a valid JSON array of strings with no extra explanation.\n"
        'Example: ["Schedule follow-up meeting in 2 weeks", "Send OncoBoost Phase III PDF", '
        '"Add Dr. Sharma to advisory board invite list"]\n'
        "Do not wrap the JSON in markdown code blocks."
    )

    response = await llm.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": input},
    ])

    content = _strip_markdown_fences(response.content)

    try:
        suggestions = json.loads(content)
        if not isinstance(suggestions, list):
            suggestions = []
        # Ensure all items are strings
        suggestions = [str(s) for s in suggestions if s]
    except Exception:
        # Fallback: extract quoted strings from the response
        suggestions = re.findall(r'"([^"]+)"', content)
        if not suggestions:
            suggestions = []

    return {
        "type": "form_update",
        "fields": {"aiSuggestedFollowups": suggestions},
        "ai_message": "Here are some suggested follow-up actions based on your interaction:",
    }
