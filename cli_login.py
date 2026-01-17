import os
import time
from login_handler import LoginHandler
from account_manager import AccountManager

def run():
    manager = AccountManager()
    handler = LoginHandler(headless=True) # Use True for headless with screenshot flow
    
    print("=== CLI Login Tool ===")
    
    # Callback to handle QR code locally
    def on_qr_code(page):
        # Save locally
        qr_filename = "login_qr_cli.png"
        if os.path.exists(qr_filename):
            os.remove(qr_filename)
            
        page.screenshot(path=qr_filename)
        abs_path = os.path.abspath(qr_filename)
        print(f"\n[Action Required] QR Code saved to: {abs_path}")
        print("Please open this image and scan it with your Xiaohongshu App.")
        
        # Try to open it automatically (Windows)
        try:
            os.startfile(abs_path)
        except:
            pass
            
        return abs_path

    def on_status(msg):
        print(f"[Status] {msg}")

    # Generate a fresh UA for this login
    ua = manager.get_user_agent_for_session()
    
    result = handler.login(
        user_agent=ua,
        qr_callback=on_qr_code,
        status_callback=on_status
    )
    
    if result["success"]:
        print("\n=== Login Successful ===")
        print(f"Nickname: {result['nickname']}")
        print(f"User ID:  {result['user_id']}")
        
        # Register
        manager.add_account(result["user_id"], result["nickname"], result["state_path"], ua)
        print("Account saved to manager.")
        
    else:
        print(f"\n=== Login Failed ===\nError: {result['error']}")

if __name__ == "__main__":
    run()
