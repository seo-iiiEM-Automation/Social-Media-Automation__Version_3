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


def generate_image(prompt: str, size: str = "1024x1024") -> str:
    """Generate an image with DALL-E and return a public URL.

    Note: the returned URL is hosted by OpenAI and expires after ~2 hours,
    but it's publicly reachable in that window, which is enough time for
    Instagram/Facebook's Graph API to fetch it when creating a media container.
    For scheduled posts more than ~1 hour out, download and re-host the image
    yourself (see README) so the link doesn't expire before publish time.
    """
    client = get_client()
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
    )
    return response.data[0].url
