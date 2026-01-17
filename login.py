# import time
# import json
# import os
# from playwright.sync_api import sync_playwright

# def run():
#     user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
#     with sync_playwright() as p:
#         print("Launching headless browser...")
#         browser = p.chromium.launch(
#             headless=True,
#             args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
#         )
#         context = browser.new_context(user_agent=user_agent)
        
#         # Add stealth script
#         context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
#         page = context.new_page()
        
#         print("Opening Xiaohongshu...")
#         page.goto("https://www.xiaohongshu.com")
#         page.wait_for_load_state("networkidle")
        
#         # 1. Check if already logged in via API
#         print("Checking login status via API...")
#         try:
#             page.screenshot(path="log/init_login_before.png")
#             # We use the page's request context to ensure cookies are sent
#             response = page.request.get("https://edith.xiaohongshu.com/api/sns/web/v2/user/me")
#             data = response.json()
#             print(f"user me API Response: {data}")
#             # 只有 code=0、有 user_id 且 guest=False 才算真正登录
#             if (data.get("code") == 0 and 
#                 data.get("data", {}).get("user_id") and 
#                 not data.get("data", {}).get("guest", True)):
#                 print("Already logged in! (Detected via user/me API)")
#                 context.storage_state(path="state.json")
#                 print("Login state saved to state.json")
#                 browser.close()
#                 return
#             else:
#                 print("Not logged in (API code: {}). Proceeding to login flow.".format(data.get("code")))
#         except Exception as e:
#             print(f"Error checking login status: {e}")

#         # 2. Ensure Login Modal is visible
#         try:
#             login_btn = page.get_by_text("登录", exact=True)
#             if login_btn.count() > 0 and login_btn.is_visible():
#                 print("Clicking login button...")
#                 login_btn.click()
#                 time.sleep(2)
#         except:
#             pass

#         # 3. Take Screenshot
#         try:
#             qr_img = page.locator("img[src*='qr']").first
#             qr_img.wait_for(state="visible", timeout=10000)
#         except:
#             print("Warning: QR code image not explicitly found, screenshotting page anyway.")
        
#         page.screenshot(path="login_qrcode.png")
#         print(f"Screenshot saved to {os.path.abspath('login_qrcode.png')}")
#         print("Please scan the QR code in the screenshot to login.")

#         # 4. Monitor Network for Login Success
#         # We need to share state between the callback and the main loop
#         login_state = {
#             "success": False,
#             "last_check_time": time.time(),
#             "status_code": -1
#         }

#         def handle_response(response):
#             if "login/qrcode/status" in response.url:
#                 login_state["last_check_time"] = time.time()
#                 try:
#                     res_data = response.json()
#                     # User provided example: {"code":0, ..., "data":{"code_status":2, ...}}
#                     print(f"login/qrcode/status Response: {res_data}")
#                     if res_data.get("code") == 0:
#                         data_obj = res_data.get("data", {})
#                         code_status = data_obj.get("code_status")
#                         login_state["status_code"] = code_status
                        
#                         if code_status == 2:
#                             login_state["success"] = True
#                             print("\nLogin Success! (Detected via network response)")
#                         elif code_status == 1:
#                             # Just waiting
#                             pass
#                 except:
#                     pass

#         page.on("response", handle_response)

#         print("Waiting for scan...")
        
#         # Wait loop
#         max_wait = 120 # 2 minutes
#         start_time = time.time()
        
#         while True:
#             if login_state["success"]:
#                 break
            
#             if time.time() - start_time > max_wait:
#                 print("\nTimeout waiting for login.")
#                 break
            
#             # Check if we are receiving updates
#             time_since_last_check = time.time() - login_state["last_check_time"]
#             if time_since_last_check > 15:
#                 print(f"\nWarning: No QR status checks detected in the last {int(time_since_last_check)} seconds. Page might be inactive.")
            
#             current_status = login_state["status_code"]
#             if current_status == 1:
#                 status_msg = "Waiting for scan (Code: 1)"
#             elif current_status == 2:
#                  status_msg = "Success (Code: 2)"
#             else:
#                  status_msg = "Initializing..."

#             print(f"\rStatus: {status_msg} ({int(time.time() - start_time)}s)...", end="")
            
#             page.wait_for_timeout(1000)

#         if login_state["success"]:
#             # Wait a moment for session to be fully established/cookies set
#             page.wait_for_timeout(2000)
#             context.storage_state(path="login_result/state.json")
#             print("\nLogin state saved to state.json")
#         else:
#             print("\nLogin failed or timed out.")

#         browser.close()

# if __name__ == "__main__":
#     run()
