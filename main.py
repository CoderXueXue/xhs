import json
import time
import os
import random
from account_manager import AccountManager
from scraper import XHSScraper

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
    scraper = XHSScraper(headless=True)
    
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

    for link in links:
        log(f"Scraping: {link}")
        
        result = scraper.scrape_note(link, state_file, user_agent)
        
        if result["success"]:
            data = result["data"]
            data["account_used"] = account['nickname']
            data["timestamp"] = time.time()
            
            # Append to results
            with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            
            log(f"Successfully scraped: {data.get('title', 'No Title')}")
        else:
            log(f"Failed: {result['error']}")
            if "Session expired" in str(result['error']):
                 # Could disable account here
                 pass
        
        # Natural delay
        time.sleep(random.uniform(2, 5))

if __name__ == "__main__":
    run()
