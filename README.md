# ⚡ AI Pulse — Autonomous Instagram Automation System

> A fully autonomous AI Instagram media system that researches, designs, writes, schedules, and publishes 5 premium AI news carousel posts every day at 9:00 AM.

## 🚀 Quick Start

### 1. Double-click `start.bat`
That's it. All services launch automatically and the dashboard opens at `http://localhost:3000`.

### 2. Manually trigger a run
```
Double-click run_now.bat
```
Or visit: `http://localhost:8000/docs` → `POST /api/trigger`

---

## 📐 Architecture

```
SCHEDULER (9:00 AM daily)
    ↓
NEWS FETCHER   → 5 RSS feeds + NewsAPI → Top 5 ranked stories
    ↓
AI WRITER      → Gemini/GPT → Headlines, captions, hashtags
    ↓
IMAGE ENGINE   → Pillow → 5 slides × 5 posts = 25 carousel images
    ↓
IMAGE SERVER   → HTTP server → Public image URLs
    ↓
IG PUBLISHER   → Meta Graph API → Carousel posts published
    ↓
ANALYTICS      → Poll metrics → SQLite → Dashboard charts
    ↓
DASHBOARD      → Next.js → http://localhost:3000
```

---

## 🔧 Configuration (`.env` file)

| Variable | Description | Required? |
|----------|-------------|-----------|
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) free tier | Optional |
| `GEMINI_API_KEY` | Google Gemini API key | Optional |
| `OPENAI_API_KEY` | OpenAI GPT-4o key | Optional |
| `INSTAGRAM_ACCESS_TOKEN` | Meta long-lived access token | For live posting |
| `INSTAGRAM_USER_ID` | Numeric IG user ID | For live posting |
| `DEMO_MODE` | `true` = simulate everything | `true` by default |
| `SCHEDULE_HOUR` | Hour to run (24h format) | `9` |

> **Without any keys**: The system runs in Demo Mode — generates real carousel images and simulates publishing.

---

## 📸 Getting Instagram Live Publishing Working

### Step 1: Create a Meta Developer App
1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create a new app → Business type
3. Add the **Instagram Graph API** product

### Step 2: Connect Instagram Business/Creator Account
1. Your Instagram account must be a **Business** or **Creator** account
2. Connect it to a **Facebook Page**
3. In your Meta App, link this Facebook Page

### Step 3: Get Access Token
1. Use the Graph API Explorer at [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer)
2. Select your app, generate a **User Token** with permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
3. Exchange for a **Long-lived token** (60-day expiry):
   ```
   https://graph.facebook.com/v21.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=YOUR_APP_ID
     &client_secret=YOUR_APP_SECRET
     &fb_exchange_token=SHORT_LIVED_TOKEN
   ```

### Step 4: Get Instagram User ID
```
GET https://graph.facebook.com/v21.0/me/accounts?access_token=YOUR_TOKEN
```
Then: `GET https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account&access_token=YOUR_TOKEN`

### Step 5: Update `.env`
```env
INSTAGRAM_ACCESS_TOKEN=your_long_lived_token
INSTAGRAM_USER_ID=your_numeric_ig_user_id
DEMO_MODE=false
```

---

## 🌐 For Production Image Hosting

The API requires images at **publicly accessible URLs**. For production:

### Option A: ngrok (simplest)
```bash
ngrok http 8888
# Copy the https URL → set IMAGE_HOST_URL in .env
```

### Option B: Cloudflare R2 / AWS S3
Upload generated images to cloud storage and update `image_server.py` to return S3 URLs.

---

## 📊 Services

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | Main monitoring UI |
| API Server | http://localhost:8000 | REST API + WebSocket |
| API Docs | http://localhost:8000/docs | Interactive API explorer |
| Image Server | http://localhost:8888 | Serves generated images |

---

## 🗂 Project Structure

```
ai-instagram-automation/
├── backend/
│   ├── main.py              # Orchestrator + APScheduler
│   ├── config.py            # All configuration
│   ├── database.py          # SQLite persistence
│   ├── news_fetcher.py      # RSS + NewsAPI fetcher
│   ├── ai_writer.py         # Gemini/GPT content writer
│   ├── image_engine.py      # Pillow carousel generator
│   ├── image_server.py      # Static image HTTP server
│   ├── instagram_publisher.py # Meta Graph API publisher
│   ├── analytics.py         # IG metrics tracker
│   ├── api_server.py        # FastAPI + WebSocket
│   └── assets/
│       ├── generated/       # Generated carousel JPGs
│       ├── thumbnails/      # Post thumbnails
│       └── fonts/           # Downloaded TTF fonts
├── dashboard/               # Next.js 15 dashboard
├── .env                     # Your API keys (never commit this)
├── start.bat                # Launch everything
├── run_now.bat              # Manual pipeline trigger
└── requirements.txt
```

---

## 🔑 AI Provider Keys

### Google Gemini (Recommended)
1. Get key at [aistudio.google.com](https://aistudio.google.com)
2. Set `GEMINI_API_KEY=...` and `AI_PROVIDER=gemini` in `.env`

### OpenAI GPT-4o
1. Get key at [platform.openai.com](https://platform.openai.com)
2. Set `OPENAI_API_KEY=...` and `AI_PROVIDER=openai` in `.env`

---

## 🕘 Timezone

The scheduler runs at `SCHEDULE_HOUR:SCHEDULE_MINUTE` in **IST (Asia/Kolkata)** by default.
To change timezone, edit `TIMEZONE` in `backend/config.py`:
```python
TIMEZONE = pytz.timezone("America/New_York")  # e.g., for EST
```

---

Built with ⚡ by AI Pulse — Powered by Google Antigravity
