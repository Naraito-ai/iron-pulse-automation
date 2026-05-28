import sys
sys.path.insert(0, 'backend')
import config
import database
database.init_db()
from news_fetcher import fetch_top_ai_news
from ai_writer import generate_all_content
from image_engine import generate_all_carousels, download_fonts
from datetime import datetime

print("Step 1: Fetching news...")
stories = fetch_top_ai_news()
print(f"  -> Got {len(stories)} stories")

print("Step 2: Generating AI content...")
content = generate_all_content(stories)
print(f"  -> Content for {len(content)} posts")
for c in content:
    print(f"     Post #{c['rank']}: {c['headline'][:60]}")

print("Step 3: Downloading fonts...")
download_fonts()
print("  -> Fonts ready")

print("Step 4: Generating carousel images...")
run_date = datetime.now().strftime("%Y-%m-%d")
result = generate_all_carousels(content, run_date)
print(f"  -> Generated {len(result)} carousels")
for r in result:
    slides = r.get("slide_paths", [])
    print(f"     Post #{r['rank']}: {len(slides)} slides")
    if slides:
        print(f"       First slide: {slides[0]}")

print("IMAGE TEST PASSED!")
