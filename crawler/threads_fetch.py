from playwright.sync_api import sync_playwright
import json
import time
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import POSTS_FILE

def fetch_following_posts():
    posts = []

    # Ensure data directory exists
    os.makedirs(os.path.dirname(POSTS_FILE), exist_ok=True)

    with sync_playwright() as p:
        # We need headed mode for manual login if not logged in
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.threads.net/")
        print("Please log in to Threads in the browser window. Once logged in and on the feed, press Enter here...")
        input()

        # Navigate to following feed
        page.goto("https://www.threads.net/following")
        time.sleep(5) # Wait for initial load

        # Scroll a bit to get more posts if needed
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            time.sleep(2)

        articles = page.query_selector_all("article")
        print(f"Found {len(articles)} posts.")

        for a in articles:
            try:
                # Threads structure might change, this is a basic heuristic
                # We try to get the text content of the post
                content = a.inner_text()
                posts.append({
                    "content": content,
                    "timestamp": time.time()
                })
            except Exception as e:
                print(f"Error parsing post: {e}")

        browser.close()

    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(posts)} posts to {POSTS_FILE}")

if __name__ == "__main__":
    fetch_following_posts()
