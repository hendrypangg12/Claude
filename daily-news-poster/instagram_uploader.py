"""Upload an image to Instagram via the Graph API.

Instagram requires the image to be accessible via a public HTTPS URL, so we
first upload the file to imgbb, then pass that URL to Instagram.
"""
import base64
import os
import time
import requests

GRAPH_VERSION = "v21.0"


def _upload_to_imgbb(image_path: str) -> str:
    """Upload to imgbb and return the public image URL."""
    api_key = os.environ["IMGBB_API_KEY"]
    with open(image_path, "rb") as fp:
        encoded = base64.b64encode(fp.read()).decode("ascii")
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": encoded, "expiration": 86400},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"]["url"]


def publish_to_instagram(image_path: str, caption: str) -> dict:
    """Upload image to imgbb, then create + publish an Instagram post.
    Returns the Graph API response for the published media."""
    ig_user_id = os.environ["IG_USER_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]

    image_url = _upload_to_imgbb(image_path)

    # Step 1: create a media container.
    create_resp = requests.post(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=60,
    )
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]

    # Step 2: wait until the container is FINISHED (IG processes async).
    for _ in range(12):
        status_resp = requests.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        status_resp.raise_for_status()
        status = status_resp.json().get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Instagram rejected the media: {status_resp.json()}")
        time.sleep(5)
    else:
        raise RuntimeError("Timed out waiting for media to finish processing")

    # Step 3: publish.
    publish_resp = requests.post(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=60,
    )
    publish_resp.raise_for_status()
    return publish_resp.json()
