"""ChatGPT (OpenAI) helpers for generating captions and images."""
import os
from openai import OpenAI

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it in Settings or your .env file.")
        _client = OpenAI(api_key=api_key)
    return _client


def generate_caption(topic: str, tone: str = "engaging", include_hashtags: bool = True,
                      platform: str = "instagram", model: str = "gpt-4o-mini") -> str:
    """Generate a social media caption using ChatGPT."""
    client = get_client()

    hashtag_instruction = (
        "End with 5-8 relevant hashtags on a new line."
        if include_hashtags else "Do not include hashtags."
    )
    system_prompt = (
        f"You write short, scroll-stopping {platform} captions. "
        f"Tone: {tone}. Keep it concise (under 150 words for the caption body). "
        f"{hashtag_instruction} Do not use markdown formatting, quotes, or asterisks."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write a caption about: {topic}"},
        ],
        max_tokens=300,
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()


def generate_image(prompt: str, size: str = "1024x1024") -> bytes:
    """Generate an image with gpt-image-2 and return the raw PNG bytes.

    Unlike the old DALL-E 3 endpoint (retired by OpenAI in May 2026),
    gpt-image-2 returns base64-encoded image data rather than a hosted URL,
    so there's no temporary link to worry about expiring — but it also means
    *we* have to host the bytes somewhere Instagram/Facebook's Graph API can
    fetch from, since their APIs require a public image URL. See
    `image_host.py` for a couple of simple ways to do that.
    """
    import base64

    client = get_client()
    response = client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        size=size,
        n=1,
    )
    b64_data = response.data[0].b64_json
    return base64.b64decode(b64_data)