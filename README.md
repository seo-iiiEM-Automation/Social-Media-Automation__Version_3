# Social Media Automation (Streamlit + ChatGPT + Meta Graph API)

Generate captions and images with ChatGPT/DALL-E, then post or schedule them
to Instagram and Facebook through Meta's **official** Graph API. No password
login, no unofficial scraping — everything goes through Meta's supported API.

## 1. Install

```bash
pip install -r requirements.txt
cp .env.example .env
# then edit .env with your real keys/tokens
```

## 2. Credentials you need

You said you already have API access — quick checklist to confirm your
tokens have the right shape:

| Variable | What it is | How to get it |
|---|---|---|
| `OPENAI_API_KEY` | ChatGPT/DALL-E access | platform.openai.com → API keys |
| `FB_PAGE_ID` | Numeric ID of your Facebook Page | Page → About, or `GET /me/accounts` |
| `FB_PAGE_ACCESS_TOKEN` | Long-lived Page token with `pages_manage_posts`, `pages_read_engagement` | Graph API Explorer → generate, then exchange for long-lived via `/oauth/access_token` |
| `IG_USER_ID` | Instagram professional account ID linked to the Page | `GET /{page-id}?fields=instagram_business_account` |
| `IG_ACCESS_TOKEN` | Token with `instagram_content_publish`, `instagram_basic` | Same token as the Page token usually works if the app has these permissions |

Page/IG tokens expire (short-lived ones in ~1 hour, long-lived in ~60 days).
For a tool you run continuously, set up a token-refresh routine or use a
System User token from Meta Business Suite, which doesn't expire on the same
cycle.

## 3. Run

```bash
streamlit run app.py
```

Open the local URL Streamlit prints. Go to **Settings** and click the two
"Test" buttons to confirm your Page and IG tokens work before posting.

## 4. How scheduling actually works

- **Facebook**: uses Meta's native `scheduled_publish_time` — the post is
  scheduled on Meta's side, so it will publish even if this app isn't running
  at that exact moment (as long as it *was* running when you queued it).
- **Instagram**: the Graph API has **no native scheduling**. This app stores
  scheduled Instagram posts in a local SQLite DB (`posts.db`) and a
  background job (`scheduler_worker.py`, checks every 60s) publishes them
  when due. **This means the app process must be running at the scheduled
  time.** For real production use, don't rely on a Streamlit tab staying
  open — instead run the worker as its own always-on process, e.g.:
  - a `cron` job that runs a small script calling `scheduler_worker.check_and_publish()`
  - a systemd service
  - a cheap always-on VM/container running `streamlit run app.py` in the background

## 5. Limitations to know about

- Instagram posts require an image (text-only IG posts aren't supported by the API).
- DALL-E image URLs expire after ~2 hours. Fine for immediate/same-day posts;
  for anything scheduled further out, download the image and host it
  somewhere permanent (S3, Cloudinary, your own server) and paste that URL instead.
- Instagram carousels, Reels, and Stories aren't implemented here — only
  single-image feed posts. Happy to add those if you need them.
- This uses the Chat Completions API (`gpt-4o-mini` by default) — swap the
  `model` argument in `ai_content.py` for a different ChatGPT model anytime.

## File overview

```
app.py                # Streamlit UI (Create / Scheduled / History / Settings tabs)
ai_content.py          # ChatGPT caption generation + DALL-E image generation
meta_api.py            # Facebook & Instagram Graph API calls
db.py                   # SQLite storage for queued/published posts
scheduler_worker.py    # Background job that publishes due posts every 60s
```
