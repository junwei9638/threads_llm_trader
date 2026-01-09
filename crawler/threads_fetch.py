from playwright.sync_api import sync_playwright
import json
import time
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import POSTS_FILE, THREADS_USERNAME, THREADS_PASSWORD

def fetch_following_posts():
    posts = []

    # Ensure data directory exists
    os.makedirs(os.path.dirname(POSTS_FILE), exist_ok=True)

    with sync_playwright() as p:
        # We need headed mode for manual login if not logged in
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to login page...")
        page.goto("https://www.threads.net/login")
        time.sleep(3)

        # Attempt Auto-Login if on login page
        try:
            # Check for username field
            user_input = page.query_selector("input[autocomplete='username']") or \
                         page.query_selector("input[name='username']")
            
            if user_input and THREADS_USERNAME and THREADS_PASSWORD:
                print(f"Attempting auto-login for user: {THREADS_USERNAME}...")
                user_input.fill(THREADS_USERNAME)
                
                pass_input = page.query_selector("input[autocomplete='current-password']") or \
                             page.query_selector("input[name='password']")
                pass_input.fill(THREADS_PASSWORD)
                
                # Click login button (usually the one with type='submit' or specific text)
                # Threads login button often in a div with role='button' or simple text
                page.keyboard.press("Enter")
                
                print("Credentials submitted. Waiting for login...")
                time.sleep(5)
                
                # Handle potential "Save Info" or 2FA if simple
                # For now, just wait for redirection
            else:
                print("Login fields not found or credentials missing. Please log in manually.")
                print("Press Enter here after you are logged in...")
                input()

        except Exception as e:
            print(f"Auto-login failed or not needed: {e}")
            print("Please ensure you are logged in manually, then press Enter...")
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
        
        import hashlib
        from datetime import datetime

        for i, a in enumerate(articles):
            try:
                # Debug first few
                text_content = a.inner_text().strip()
                if not text_content:
                    continue
                
                # Simple filter to avoid buttons/menus
                if len(text_content) < 10:
                    continue
                
                # Try to extract influencer name
                # Heuristic: split lines, usually first line is name or "Name\nTime"
                lines = text_content.split('\n')
                influencer = lines[0].strip() if lines else "Unknown"
                
                # Timestamp
                now_ts = time.time()
                fetch_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # Generate stable ID
                post_id = f"threads_{hashlib.md5(text_content.encode('utf-8')).hexdigest()[:8]}"

                posts.append({
                    "id": post_id,
                    "content": text_content,
                    "timestamp": now_ts,
                    "influencer": influencer,
                    "post_time": fetch_time_str, # Threads doesn't easily expose absolute time in text, using fetch time as proxy
                    "fetch_time": fetch_time_str
                })
                if i < 3:
                    print(f"Sample post {i}: ID={post_id} | {influencer} | {text_content[:30]}...")
            except Exception as e:
                print(f"Error parsing post {i}: {e}")

        browser.close()

    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(posts)} posts to {POSTS_FILE}")

if __name__ == "__main__":
    fetch_following_posts()
