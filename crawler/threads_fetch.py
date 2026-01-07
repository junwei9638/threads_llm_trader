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
        print("Navigating to following feed...")
        page.goto("https://www.threads.net/following")
        
        # Wait for feed to load explicitly
        try:
            print("Waiting for posts to load...")
            # Threads generic post container often has role="article" or specific classes, 
            # but 'article' tag is semantic and usually present.
            # We also wait longer.
            page.wait_for_selector("div[data-pressable-container='true']", timeout=10000)
        except Exception as e:
            print(f"Warning: Timeout waiting for specific post selector: {e}")

        # Scroll to load more
        print("Scrolling to load more posts...")
        for i in range(5):
            page.mouse.wheel(0, 3000)
            time.sleep(2)

        # Try multiple selectors
        articles = page.query_selector_all("div[data-pressable-container='true']") # Common wrapper for posts
        if not articles:
             articles = page.query_selector_all("article")
        
        print(f"Found {len(articles)} potential post elements.")

        for i, a in enumerate(articles):
            try:
                # Debug first few
                text_content = a.inner_text().strip()
                if not text_content:
                    continue
                
                # Simple filter to avoid buttons/menus
                if len(text_content) < 10:
                    continue

                posts.append({
                    "content": text_content,
                    "timestamp": time.time()
                })
                if i < 3:
                    print(f"Sample post {i}: {text_content[:50]}...")
            except Exception as e:
                print(f"Error parsing post {i}: {e}")

        browser.close()

    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(posts)} posts to {POSTS_FILE}")

if __name__ == "__main__":
    fetch_following_posts()
