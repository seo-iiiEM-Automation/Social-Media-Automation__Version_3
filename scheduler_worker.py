"""Background job that checks the DB every minute and publishes due posts.

Started once per Streamlit process via start_scheduler(). Uses APScheduler's
BackgroundScheduler so it keeps running as long as the app process is alive.
For production, run this as a separate always-on process (see README) rather
than relying on a browser tab keeping Streamlit's process warm.
"""
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

import db
import meta_api

_scheduler = None


def _publish_one(row):
    platform = row["platform"]
    caption = row["caption"]
    image_url = row["image_url"]

    try:
        if platform == "instagram":
            ig_user_id = os.environ["IG_USER_ID"]
            ig_token = os.environ["IG_ACCESS_TOKEN"]
            result_id = meta_api.publish_to_instagram(ig_user_id, ig_token, caption, image_url)
        elif platform == "facebook":
            page_id = os.environ["FB_PAGE_ID"]
            page_token = os.environ["FB_PAGE_ACCESS_TOKEN"]
            result_id = meta_api.publish_to_facebook(page_id, page_token, caption, image_url)
        else:
            raise ValueError(f"Unknown platform: {platform}")

        db.mark_published(row["id"], result_id)
    except Exception as e:
        db.mark_failed(row["id"], e)


def check_and_publish():
    now_iso = datetime.utcnow().isoformat()
    due = db.get_pending_due(now_iso)
    for row in due:
        _publish_one(row)


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    db.init_db()
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(check_and_publish, "interval", minutes=1, id="publish_due_posts")
    _scheduler.start()
    return _scheduler
