import time
import random
from playwright.sync_api import sync_playwright

class XHSScraper:
    def __init__(self, headless=True):
        self.headless = headless

    def scrape_note(self, url, account_state_path, user_agent):
        """
        Scrapes a single XHS note.
        Returns a dictionary with result or error.
        """
        result = {
            "success": False,
            "data": {},
            "error": None
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
                )
                
                context = browser.new_context(
                    storage_state=account_state_path,
                    user_agent=user_agent
                )
                
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                page = context.new_page()
                
                print(f"[Scraper] Navigating to: {url}")
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle")
                
                # Check for login redirect
                if "login" in page.url:
                    result["error"] = "Session expired (Redirected to login)"
                    browser.close()
                    return result

                # Extract Data
                data = {}
                data["title"] = page.title()
                data["url"] = url
                
                # Content extraction
                try:
                    content_selector = ".note-content" 
                    if page.locator(content_selector).count() > 0:
                        data["content"] = page.locator(content_selector).inner_text()
                    else:
                        data["content"] = page.locator('meta[name="description"]').get_attribute("content")
                except Exception as e:
                    data["content"] = f"Extraction error: {str(e)}"
                
                # Additional fields can be added here (likes, date, etc.)
                
                result["data"] = data
                result["success"] = True
                
                browser.close()
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
