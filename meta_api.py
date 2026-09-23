"""Instagram & Facebook publishing via Meta's official Graph API.

Requires:
- A Facebook Page (Page ID + Page Access Token with pages_manage_posts,
  pages_read_engagement)
- An Instagram professional account linked to that Page (IG User ID +
  access token with instagram_content_publish)

All calls use the official Graph API — no scraping, no password login.
"""
import time
import requests

GRAPH_VERSION = "v21.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


class MetaAPIError(Exception):
    pass


def _check(resp: requests.Response):
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            detail = resp.text
        raise MetaAPIError(detail)
    return resp.json()


def publish_to_facebook(page_id: str, page_access_token: str, caption: str,
                         image_url: str | None = None, scheduled_time_epoch: int | None = None):
    """Post to a Facebook Page. Supports native scheduling via scheduled_time_epoch
    (unix timestamp, must be 10 min to 6 months in the future)."""
    params = {
        "message": caption,
        "access_token": page_access_token,
    }
    if scheduled_time_epoch:
        params["published"] = "false"
        params["scheduled_publish_time"] = scheduled_time_epoch

    if image_url:
        endpoint = f"{GRAPH_URL}/{page_id}/photos"
        params["url"] = image_url
        if scheduled_time_epoch:
            params["published"] = "false"
            params["scheduled_publish_time"] = scheduled_time_epoch
    else:
        endpoint = f"{GRAPH_URL}/{page_id}/feed"

    resp = requests.post(endpoint, params=params, timeout=30)
    data = _check(resp)
    return data.get("id") or data.get("post_id")


def publish_to_instagram(ig_user_id: str, access_token: str, caption: str, image_url: str):
    """Publish an image post to Instagram. Two-step: create container, then publish.
    Instagram's Graph API has no native scheduling — call this at the moment
    you want the post to go live (the scheduler_worker does this for you)."""
    if not image_url:
        raise MetaAPIError("Instagram posts require an image_url.")

    # Step 1: create media container
    create_resp = requests.post(
        f"{GRAPH_URL}/{ig_user_id}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    container = _check(create_resp)
    creation_id = container["id"]

    # Step 2: poll container status until it's ready (usually a few seconds)
    for _ in range(10):
        status_resp = requests.get(
            f"{GRAPH_URL}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=15,
        )
        status = _check(status_resp).get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise MetaAPIError("Instagram media container failed to process.")
        time.sleep(2)

    # Step 3: publish
    publish_resp = requests.post(
        f"{GRAPH_URL}/{ig_user_id}/media_publish",
        params={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    data = _check(publish_resp)
    return data["id"]
