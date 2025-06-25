from openai import OpenAI

from guardian.config import get_settings


def groq_chat(messages, max_tokens=512, temperature=0.7):
    settings = get_settings()
    client = OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url=settings.GROQ_API_ENDPOINT,
    )
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content
