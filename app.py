import os
from datetime import datetime, date, time as dtime

import streamlit as st
from dotenv import load_dotenv

import db
import ai_content
import image_host
import meta_api
from scheduler_worker import start_scheduler

load_dotenv()
st.set_page_config(page_title="Social Media Automation", page_icon="\U0001F4F1", layout="wide")

db.init_db()
start_scheduler()  # runs in background thread, checks every minute for due posts

if "generated_caption" not in st.session_state:
    st.session_state.generated_caption = ""
if "generated_image_url" not in st.session_state:
    st.session_state.generated_image_url = ""

st.title("\U0001F4F1 Social Media Automation")
st.caption("ChatGPT-generated content, published to Instagram & Facebook via the official Meta Graph API.")

tab_create, tab_scheduled, tab_history, tab_settings = st.tabs(
    ["\u2728 Create Post", "\U0001F553 Scheduled", "\U0001F4CB History", "\u2699\uFE0F Settings"]
)

# ---------------------------------------------------------------------------
# CREATE POST
# ---------------------------------------------------------------------------
with tab_create:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Generate content")
        topic = st.text_area("What's the post about?", placeholder="e.g. Launching our new eco-friendly water bottle")
        tone = st.selectbox("Tone", ["engaging", "professional", "funny", "inspirational", "casual", "bold"])
        platform_for_caption = st.selectbox("Optimize caption for", ["instagram", "facebook"])
        include_hashtags = st.checkbox("Include hashtags", value=True)

        if st.button("Generate caption with ChatGPT", use_container_width=True):
            if not topic.strip():
                st.warning("Enter a topic first.")
            else:
                with st.spinner("Asking ChatGPT..."):
                    try:
                        st.session_state.generated_caption = ai_content.generate_caption(
                            topic, tone=tone, include_hashtags=include_hashtags, platform=platform_for_caption
                        )
                    except Exception as e:
                        st.error(f"Caption generation failed: {e}")

        image_prompt = st.text_input("Image description (optional, for gpt-image-2)", placeholder="e.g. a minimalist product shot of a water bottle on a wooden table")
        if st.button("Generate image with ChatGPT (gpt-image-2)", use_container_width=True):
            if not image_prompt.strip():
                st.warning("Enter an image description first.")
            else:
                with st.spinner("Generating image..."):
                    try:
                        image_bytes = ai_content.generate_image(image_prompt)
                        st.session_state.generated_image_url = image_host.host_image(image_bytes)
                    except Exception as e:
                        st.error(f"Image generation failed: {e}")

    with col_right:
        st.subheader("2. Review & edit")
        caption = st.text_area("Caption", value=st.session_state.generated_caption, height=220, key="caption_editor")
        image_url = st.text_input("Image URL (auto-filled after generation, or paste your own public URL)",
                                   value=st.session_state.generated_image_url, key="image_url_editor")
        if image_url:
            st.image(image_url, caption="Preview", use_container_width=True)

    st.divider()
    st.subheader("3. Publish")

    pub_col1, pub_col2, pub_col3 = st.columns([1, 1, 1])
    with pub_col1:
        target_platform = st.selectbox("Platform", ["instagram", "facebook"], key="publish_platform")
    with pub_col2:
        when = st.radio("When", ["Post now", "Schedule for later"], horizontal=True)
    with pub_col3:
        if when == "Schedule for later":
            sched_date = st.date_input("Date", min_value=date.today())
            sched_time = st.time_input("Time", value=dtime(hour=9, minute=0))
        else:
            sched_date, sched_time = None, None

    if target_platform == "instagram" and not image_url:
        st.info("Instagram requires an image. Generate one above or paste a public image URL.")

    if st.button("\U0001F680 Queue this post", type="primary", use_container_width=True):
        if not caption.strip():
            st.error("Caption can't be empty.")
        elif target_platform == "instagram" and not image_url:
            st.error("Instagram posts need an image URL.")
        else:
            scheduled_iso = None
            if when == "Schedule for later":
                scheduled_dt = datetime.combine(sched_date, sched_time)
                if scheduled_dt <= datetime.now():
                    st.error("Scheduled time must be in the future.")
                    st.stop()
                scheduled_iso = scheduled_dt.isoformat()

            db.add_post(target_platform, caption.strip(), image_url or None, scheduled_iso)
            if scheduled_iso:
                st.success(f"Post queued for {scheduled_iso}. It'll publish automatically (keep this app running).")
            else:
                st.success("Post queued — it will publish within the next minute (background check runs every 60s).")
            st.session_state.generated_caption = ""
            st.session_state.generated_image_url = ""

# ---------------------------------------------------------------------------
# SCHEDULED
# ---------------------------------------------------------------------------
with tab_scheduled:
    st.subheader("Pending posts")
    rows = [r for r in db.get_all_posts() if r["status"] == "pending"]
    if not rows:
        st.info("No pending posts.")
    for r in rows:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{r['platform'].capitalize()}** — scheduled: {r['scheduled_time'] or 'ASAP'}")
                st.write(r["caption"][:200] + ("..." if len(r["caption"]) > 200 else ""))
                if r["image_url"]:
                    st.caption(f"Image: {r['image_url'][:80]}...")
            with c2:
                if st.button("Cancel", key=f"cancel_{r['id']}"):
                    db.delete_post(r["id"])
                    st.rerun()

# ---------------------------------------------------------------------------
# HISTORY
# ---------------------------------------------------------------------------
with tab_history:
    st.subheader("Published & failed posts")
    rows = [r for r in db.get_all_posts() if r["status"] != "pending"]
    if not rows:
        st.info("Nothing published yet.")
    for r in rows:
        icon = "\u2705" if r["status"] == "published" else "\u274C"
        with st.container(border=True):
            st.markdown(f"{icon} **{r['platform'].capitalize()}** — {r['status']}")
            st.write(r["caption"][:200] + ("..." if len(r["caption"]) > 200 else ""))
            if r["status"] == "published":
                st.caption(f"Result ID: {r['result_id']}")
            else:
                st.caption(f"Error: {r['error']}")

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
with tab_settings:
    st.subheader("API credentials")
    st.caption("These are read from environment variables / a .env file. Set them there rather than typing "
                "secrets into the UI. See README.md for how to obtain each value.")

    def status_row(name):
        val = os.environ.get(name)
        st.write(f"{'✅' if val else '⬜'} `{name}`" + ("" if val else " — not set"))

    status_row("OPENAI_API_KEY")
    status_row("FB_PAGE_ID")
    status_row("FB_PAGE_ACCESS_TOKEN")
    status_row("IG_USER_ID")
    status_row("IG_ACCESS_TOKEN")

    st.divider()
    st.subheader("Connection test")
    if st.button("Test Facebook Page token"):
        try:
            import requests
            r = requests.get(
                f"{meta_api.GRAPH_URL}/{os.environ['FB_PAGE_ID']}",
                params={"fields": "name", "access_token": os.environ["FB_PAGE_ACCESS_TOKEN"]},
            )
            r.raise_for_status()
            st.success(f"Connected to Page: {r.json().get('name')}")
        except Exception as e:
            st.error(f"Failed: {e}")

    if st.button("Test Instagram token"):
        try:
            import requests
            r = requests.get(
                f"{meta_api.GRAPH_URL}/{os.environ['IG_USER_ID']}",
                params={"fields": "username", "access_token": os.environ["IG_ACCESS_TOKEN"]},
            )
            r.raise_for_status()
            st.success(f"Connected to IG account: @{r.json().get('username')}")
        except Exception as e:
            st.error(f"Failed: {e}")