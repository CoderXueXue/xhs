import json
import time
import os
import random
from playwright.sync_api import sync_playwright
from account_manager import AccountManager

LINKS_FILE = "links.txt"
RESULTS_FILE = os.path.join("data", "results.jsonl")
LOG_FILE = os.path.join("data", "scraper.log")

def log(message):
    if not os.path.exists("data"):
        os.makedirs("data")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def run():
    manager = AccountManager()
    
    # Select an account
    account = manager.get_random_active_account()
    if not account:
        log("Error: No active accounts found. Please add an account via the Web UI.")
        return

    log(f"Using account: {account['nickname']} (ID: {account['id']})")
    state_file = account['state_file']
    user_agent = account['user_agent']

    if not os.path.exists(state_file):
        log(f"Error: State file {state_file} missing.")
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
        browser = p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            storage_state=state_file,
            user_agent=user_agent
        )
        
        # Add stealth scripts
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
                    # Optionally mark account as invalid here
                    break
                
                # Extract data
                title = page.title()
                
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
                    "account_used": account['nickname'],
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
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                log(f"Error processing {link}: {str(e)}")

        browser.close()

if __name__ == "__main__":
    run()
