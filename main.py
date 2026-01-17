import json
import time
import os
from playwright.sync_api import sync_playwright

STATE_FILE = "state.json"
LINKS_FILE = "links.txt"
RESULTS_FILE = "results.jsonl"
LOG_FILE = "scraper.log"

def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def run():
    if not os.path.exists(STATE_FILE):
        log(f"Error: {STATE_FILE} not found. Please run login.py first.")
        return

    if not os.path.exists(LINKS_FILE):
        log(f"Error: {LINKS_FILE} not found.")
        return

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    if not links:
        log("No links found in links.txt")
        return

    with sync_playwright() as p:
        # Use stealth args to minimize detection
        # Note: On Windows headless=True is the standard headless mode. 
        # Xvfb is Linux only.
        browser = p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        
        # User Agent is critical for headless mode
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        context = browser.new_context(
            storage_state=STATE_FILE,
            user_agent=user_agent
        )
        
        # Add stealth scripts if needed (basic evasion)
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()

        for link in links:
            try:
                log(f"Navigating to: {link}")
                page.goto(link, timeout=60000)
                page.wait_for_load_state("networkidle")
                
                # Basic stability check
                if "login" in page.url:
                    log("Warning: Redirected to login page. Session might be expired.")
                    break
                
                # Extract data
                # Priority 1: Title
                title = page.title()
                
                # Priority 2: Description/Content (Simple DOM approach for now)
                # Trying common XHS selectors (these might change, so we use generic fallbacks)
                try:
                    # Attempt to get the note content
                    content_selector = ".note-content" # Hypothetical
                    if page.locator(content_selector).count() > 0:
                        content = page.locator(content_selector).inner_text()
                    else:
                        # Fallback to description meta
                        content = page.locator('meta[name="description"]').get_attribute("content")
                except Exception as e:
                    content = f"Extraction failed: {str(e)}"

                result = {
                    "url": link,
                    "title": title,
                    "content": content,
                    "timestamp": time.time()
                }
                
                # Append to results
                with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                
                log(f"Successfully scraped: {title}")
                
                # Natural delay
                time.sleep(2)

            except Exception as e:
                log(f"Error processing {link}: {str(e)}")

        browser.close()

if __name__ == "__main__":
    run()
