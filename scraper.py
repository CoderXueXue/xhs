import time
import random
import os
from playwright.sync_api import sync_playwright

class XHSScraper:
    def __init__(self, headless=True):
        self.headless = headless

    def _save_debug_screenshot(self, page, name_prefix="debug"):
        """
        Saves a screenshot of the current page for debugging purposes.
        """
        screenshot_dir = os.path.join("log", "debug_screenshots")
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{name_prefix}_{timestamp}.png"
        filepath = os.path.join(screenshot_dir, filename)
        
        try:
            page.screenshot(path=filepath)
            print(f"[Scraper] Saved debug screenshot: {filepath}")
        except Exception as e:
            print(f"[Scraper] Failed to save screenshot: {e}")

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
                
                try:
                    print(f"[Scraper] Navigating to: {url}")
                    page.goto(url, timeout=60000)
                    page.wait_for_load_state("networkidle")
                    
                    print(f"[Scraper] Page loaded. URL: {page.url}")
                    self._save_debug_screenshot(page, "after_navigation")

                    # Check for login redirect
                    if "login" in page.url:
                        self._save_debug_screenshot(page, "login_redirect")
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
                        self._save_debug_screenshot(page, "extraction_error")
                    
                    # Additional fields can be added here (likes, date, etc.)
                    
                    result["data"] = data
                    result["success"] = True
                
                except Exception as e:
                    self._save_debug_screenshot(page, "scrape_error")
                    raise e
                finally:
                    browser.close()
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
