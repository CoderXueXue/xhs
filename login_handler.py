import time
import os
import json
from playwright.sync_api import sync_playwright

class LoginHandler:
    def __init__(self, headless=True):
        self.headless = headless

    def login(self, user_agent, qr_callback=None, status_callback=None):
        """
        Executes the login flow.
        
        Args:
            user_agent (str): The UA to use.
            qr_callback (func): Called when QR code is ready. Args: (page_object) -> str (path to saved image)
            status_callback (func): Called with status updates. Args: (msg)
        
        Returns:
            dict: {success: bool, user_id: str, nickname: str, state_path: str, error: str}
        """
        result = {
            "success": False,
            "user_id": None,
            "nickname": None,
            "state_path": None,
            "error": None
        }

        def log(msg):
            if status_callback:
                status_callback(msg)
            else:
                print(f"[LoginHandler] {msg}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
                )
                context = browser.new_context(user_agent=user_agent)
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                page = context.new_page()
                
                log("Opening Xiaohongshu...")
                page.goto("https://www.xiaohongshu.com")
                log("Page loaded.")
                
                # Setup network interception for QR status
                qr_status = {"code": -1}
                def handle_response(response):
                    if "login/qrcode/status" in response.url:
                        try:
                            res = response.json()
                            if res.get("code") == 0:
                                qr_status["code"] = res.get("data", {}).get("code_status", -1)
                        except:
                            pass
                page.on("response", handle_response)
                
                # Click login button
                try:
                    page.wait_for_load_state("networkidle")
                    login_btn = page.get_by_text("登录", exact=True)
                    if login_btn.count() > 0 and login_btn.is_visible():
                        login_btn.click()
                        time.sleep(1)
                except:
                    pass
                
                log("Waiting for QR code...")
                try:
                    qr_img = page.locator("img[src*='qr']").first
                    qr_img.wait_for(state="visible", timeout=15000)
                except:
                    log("QR code element detection timed out, falling back to full page.")

                # Callback to handle QR code (e.g., screenshot)
                if qr_callback:
                    qr_path = qr_callback(page)
                    log(f"QR Code captured at: {qr_path}")
                
                log("Waiting for scan...")
                
                # Polling loop
                start_time = time.time()
                success = False
                
                while time.time() - start_time < 120:
                    if qr_status["code"] == 2:
                        success = True
                        break
                    
                    # Double check via API
                    if int(time.time()) % 5 == 0:
                        try:
                            me_res = page.request.get("https://edith.xiaohongshu.com/api/sns/web/v2/user/me")
                            me_data = me_res.json()
                            if me_data.get("code") == 0 and me_data.get("data", {}).get("user_id") and not me_data.get("data", {}).get("guest", True):
                                success = True
                                break
                        except:
                            pass
                    
                    time.sleep(1)
                
                if success:
                    log("Login successful! Fetching user info...")
                    
                    # Get user info
                    try:
                        me_res = page.request.get("https://edith.xiaohongshu.com/api/sns/web/v2/user/me")
                        me_data = me_res.json()
                        user_data = me_data.get("data", {})
                        user_id = user_data.get("user_id", f"user_{int(time.time())}")
                        nickname = user_data.get("nickname", "Unknown")
                    except:
                        user_id = f"user_{int(time.time())}"
                        nickname = "Unknown"
                    
                    # Save state
                    if not os.path.exists(os.path.join("data", "accounts_state")):
                         os.makedirs(os.path.join("data", "accounts_state"), exist_ok=True)
                         
                    state_filename = f"{user_id}_state.json"
                    state_path = os.path.join("data", "accounts_state", state_filename)
                    context.storage_state(path=state_path)
                    
                    result["success"] = True
                    result["user_id"] = user_id
                    result["nickname"] = nickname
                    result["state_path"] = state_path
                    
                else:
                    result["error"] = "Timeout waiting for scan"
                    log("Login timed out.")

                browser.close()
                
        except Exception as e:
            result["error"] = str(e)
            log(f"Error: {e}")

        return result
