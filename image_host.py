"""Get a public URL for raw image bytes.

Instagram/Facebook's Graph API requires a publicly reachable image URL when
creating a post — it won't accept raw bytes. Since gpt-image-2 returns base64
bytes (not a hosted URL like the old DALL-E 3 did), we need to host the image
ourselves somewhere public before handing it to Meta's API.

Primary method: upload the image to your own Facebook Page as an
*unpublished* photo, then read back the CDN URL Facebook generates for it.
This is reliable (it's Meta's own infrastructure, not a third-party free
host), doesn't need any extra signup since you already have a Page token,
and the photo never shows up on your Page's timeline because it's never
published. Falls back to catbox.moe if Facebook credentials aren't set.
"""
import io
import os
import uuid

import requests

GRAPH_VERSION = "v21.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


def upload_via_facebook(image_bytes: bytes) -> str:
    """Upload as an unpublished photo to your FB Page and return its public
    CDN URL. Requires FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN env vars."""
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]

    upload_resp = requests.post(
        f"{GRAPH_URL}/{page_id}/photos",
        params={"published": "false", "access_token": token},
        files={"source": ("image.png", io.BytesIO(image_bytes), "image/png")},
        timeout=30,
    )
    if upload_resp.status_code >= 400:
        raise RuntimeError(f"Facebook photo upload failed: {upload_resp.text}")
    photo_id = upload_resp.json()["id"]

    detail_resp = requests.get(
        f"{GRAPH_URL}/{photo_id}",
        params={"fields": "images", "access_token": token},
        timeout=15,
    )
    detail_resp.raise_for_status()
    images = detail_resp.json().get("images", [])
    if not images:
        raise RuntimeError("Facebook returned no image renditions for the uploaded photo.")
    return images[0]["source"]  # largest rendition first


def upload_to_catbox(image_bytes: bytes, filename: str = None) -> str:
    """Fallback: upload bytes to catbox.moe and return the public URL."""
    filename = filename or f"{uuid.uuid4().hex}.png"
    resp = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": (filename, io.BytesIO(image_bytes), "image/png")},
        headers={"User-Agent": "Mozilla/5.0 (compatible; social-automation-app/1.0)"},
        timeout=30,
    )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"catbox upload failed: {url}")
    return url


def upload_to_s3(image_bytes: bytes, filename: str = None) -> str:
    """Optional third option: upload to your own S3 bucket instead. Requires
    boto3 and these env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME, AWS_REGION. Bucket must allow public-read on the object.
    """
    import boto3

    filename = filename or f"{uuid.uuid4().hex}.png"
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    bucket = os.environ["S3_BUCKET_NAME"]
    s3.put_object(Bucket=bucket, Key=filename, Body=image_bytes, ContentType="image/png", ACL="public-read")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return f"https://{bucket}.s3.{region}.amazonaws.com/{filename}"


def host_image(image_bytes: bytes, filename: str = None) -> str:
    """Entry point used by the app. Tries Facebook first (most reliable given
    you already have Page credentials), falls back to catbox if that fails."""
    if os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_ACCESS_TOKEN"):
        try:
            return upload_via_facebook(image_bytes)
        except Exception:
            pass  # fall through to catbox new One
    return upload_to_catbox(image_bytes, filename)