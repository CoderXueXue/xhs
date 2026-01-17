from flask import Flask, render_template, jsonify, request, redirect, url_for
import threading
import time
import os
import json
from playwright.sync_api import sync_playwright
from account_manager import AccountManager

app = Flask(__name__)
manager = AccountManager()

# Global state for the current login session
login_session = {
    "status": "idle", # idle, initializing, waiting_scan, success, failed, timeout
    "qr_path": None,
    "message": "",
    "logs": []
}

def log_msg(msg):
    print(f"[WebLogin] {msg}")
    login_session["logs"].append(f"{time.strftime('%H:%M:%S')} - {msg}")

def login_worker_thread(user_agent):
    global login_session
    login_session["status"] = "initializing"
    login_session["qr_path"] = None
    login_session["logs"] = []
    
    log_msg("Starting login worker...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(user_agent=user_agent)
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            log_msg("Navigating to Xiaohongshu...")
            page.goto("https://www.xiaohongshu.com")
            
            # Setup network interception
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
            
            # Click login button if needed
            try:
                page.wait_for_load_state("networkidle")
                login_btn = page.get_by_text("登录", exact=True)
                if login_btn.count() > 0 and login_btn.is_visible():
                    login_btn.click()
                    time.sleep(1)
            except:
                pass
                
            # Wait for QR code
            log_msg("Waiting for QR code...")
            try:
                qr_img = page.locator("img[src*='qr']").first
                qr_img.wait_for(state="visible", timeout=15000)
            except:
                log_msg("QR code element not found, screenshotting full page")
            
            # Screenshot to static folder
            qr_filename = f"qr_{int(time.time())}.png"
            qr_abs_path = os.path.join(app.root_path, "static", qr_filename)
            page.screenshot(path=qr_abs_path)
            
            login_session["qr_path"] = f"/static/{qr_filename}"
            login_session["status"] = "waiting_scan"
            log_msg("QR Code ready. Please scan.")
            
            # Wait loop
            start_time = time.time()
            success = False
            
            while time.time() - start_time < 120: # 2 min timeout
                if qr_status["code"] == 2:
                    success = True
                    break
                if qr_status["code"] == 1:
                    # Waiting scan
                    pass
                
                # Check API for user info as double check
                # Sometimes network intercept misses
                if int(time.time()) % 5 == 0:
                    try:
                        me_res = page.request.get("https://edith.xiaohongshu.com/api/sns/web/v2/user/me")
                        me_data = me_res.json()
                        log_msg(f"API check - me_data Code: {me_data}")
                        if me_data.get("code") == 0 and me_data.get("data", {}).get("user_id") and not me_data.get("data", {}).get("guest", True) :
                            success = True
                            break
                    except:
                        pass
                
                time.sleep(1)
            
            if success:
                log_msg("Login successful!")
                login_session["status"] = "processing"
                
                # Get user info
                user_id = "unknown"
                nickname = "Unknown"
                
                try:
                    me_res = page.request.get("https://edith.xiaohongshu.com/api/sns/web/v2/user/me")
                    me_data = me_res.json()
                    user_data = me_data.get("data", {})
                    user_id = user_data.get("user_id", "unknown")
                    nickname = user_data.get("nickname", "Unknown User")
                except:
                    log_msg("Failed to fetch user profile, using ID as name")
                    user_id = f"user_{int(time.time())}"
                
                # Save state
                state_filename = f"{user_id}_state.json"
                state_path = os.path.join("data", "accounts_state", state_filename)
                context.storage_state(path=state_path)
                
                # Register account
                manager.add_account(user_id, nickname, state_path, user_agent)
                
                login_session["status"] = "success"
                login_session["message"] = f"Added account: {nickname}"
                
            else:
                log_msg("Login timed out.")
                login_session["status"] = "timeout"
            
            browser.close()
            
    except Exception as e:
        log_msg(f"Error: {str(e)}")
        login_session["status"] = "failed"
        login_session["message"] = str(e)


@app.route('/')
def index():
    accounts = manager.get_all_accounts()
    return render_template('index.html', accounts=accounts)

@app.route('/add')
def add_account_page():
    return render_template('add_account.html')

@app.route('/api/start_login', methods=['POST'])
def start_login():
    if login_session["status"] in ["initializing", "waiting_scan"]:
        return jsonify({"status": "busy", "message": "Login already in progress"})
    
    ua = manager.get_user_agent_for_session()
    thread = threading.Thread(target=login_worker_thread, args=(ua,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/login_status')
def get_status():
    return jsonify(login_session)

@app.route('/delete/<user_id>')
def delete_account(user_id):
    manager.delete_account(user_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
