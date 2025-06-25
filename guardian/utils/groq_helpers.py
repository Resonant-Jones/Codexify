import base64
import os

from groq import Groq


def make_groq_vision_payload(text: str, image_path: str) -> list[dict]:
    """Prepare a Groq-compatible vision prompt with base64 image data."""
    with open(image_path, "rb") as img:
        encoded = base64.b64encode(img.read()).decode("utf-8")
    return [
        {"type": "text", "text": text},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
        },
    ]


def make_groq_vision_url_payload(text: str, image_url: str) -> list[dict]:
    """Prepare a Groq-compatible vision prompt with an image from a public URL."""
    return [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]


def run_groq_vision_url(
    image_url: str, prompt_text: str = "What's in this image?"
) -> str:
    """Run a Groq vision model on an image URL and return the response text."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    messages = [
        {
            "role": "user",
            "content": make_groq_vision_url_payload(prompt_text, image_url),
        }
    ]
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
    )
    return completion.choices[0].message.content


def run_groq_vision_file(
    image_path: str, prompt_text: str = "What's in this image?"
) -> str:
    """Run a Groq vision model on a local image file and return the response text."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    messages = [
        {"role": "user", "content": make_groq_vision_payload(prompt_text, image_path)}
    ]
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=messages,
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
    )
    return completion.choices[0].message.content
