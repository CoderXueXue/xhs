from flask import Flask, render_template, jsonify, request, redirect, url_for
import threading
import time
import os
import json
from account_manager import AccountManager
from login_handler import LoginHandler
from scraper import XHSScraper

app = Flask(__name__)
manager = AccountManager()

# Global state for the current login session
login_session = {
    "status": "idle", # idle, initializing, waiting_scan, processing, success, failed, timeout
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
    
    handler = LoginHandler(headless=True)
    
    def on_qr_code(page):
        # Screenshot to static folder
        qr_filename = f"qr_{int(time.time())}.png"
        qr_abs_path = os.path.join(app.root_path, "static", qr_filename)
        page.screenshot(path=qr_abs_path)
        
        login_session["qr_path"] = f"/static/{qr_filename}"
        login_session["status"] = "waiting_scan"
        return qr_abs_path
    
    def on_status(msg):
        log_msg(msg)
        
    result = handler.login(
        user_agent=user_agent,
        qr_callback=on_qr_code,
        status_callback=on_status
    )
    
    if result["success"]:
        login_session["status"] = "processing"
        
        # Register account
        manager.add_account(result["user_id"], result["nickname"], result["state_path"], user_agent)
        
        login_session["status"] = "success"
        login_session["message"] = f"Added account: {result['nickname']}"
    else:
        login_session["status"] = "failed"
        login_session["message"] = result.get("error", "Unknown error")


@app.route('/')
def index():
    accounts = manager.get_all_accounts()
    return render_template('index.html', accounts=accounts)

@app.route('/add')
def add_account_page():
    return render_template('add_account.html')

@app.route('/scrape', methods=['GET', 'POST'])
def scrape_page():
    result = None
    if request.method == 'POST':
        url = request.form.get('url')
        account_id = request.form.get('account_id')
        
        account = None
        if account_id:
            accounts = manager.get_all_accounts()
            account = next((a for a in accounts if a['id'] == account_id), None)
        else:
            account = manager.get_random_active_account()
            
        if account and url:
            scraper = XHSScraper(headless=True)
            scrape_res = scraper.scrape_note(url, account['state_file'], account['user_agent'])
            result = scrape_res
            result["account_used"] = account['nickname']
            
    accounts = manager.get_all_accounts()
    return render_template('scrape.html', accounts=accounts, result=result)

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
