import json
import os
import random
import time

DATA_DIR = "data"
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")
ACCOUNTS_DIR = os.path.join(DATA_DIR, "accounts_state")

# High quality UAs to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

class AccountManager:
    def __init__(self):
        self._ensure_setup()

    def _ensure_setup(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(ACCOUNTS_DIR):
            os.makedirs(ACCOUNTS_DIR)
        if not os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def get_all_accounts(self):
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def save_accounts(self, accounts):
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)

    def add_account(self, user_id, nickname, state_path, user_agent=None):
        accounts = self.get_all_accounts()
        
        # Check if exists, update if so
        existing = next((a for a in accounts if a['id'] == user_id), None)
        
        new_account = {
            "id": user_id,
            "nickname": nickname,
            "state_file": state_path,
            "user_agent": user_agent or random.choice(USER_AGENTS),
            "status": "active",
            "last_used": 0,
            "added_at": time.time()
        }
        
        if existing:
            # Update existing
            existing.update(new_account)
        else:
            accounts.append(new_account)
            
        self.save_accounts(accounts)
        return new_account

    def get_random_active_account(self):
        accounts = self.get_all_accounts()
        active = [a for a in accounts if a.get('status') == 'active']
        if not active:
            return None
        return random.choice(active)

    def disable_account(self, user_id):
        accounts = self.get_all_accounts()
        for a in accounts:
            if a['id'] == user_id:
                a['status'] = 'disabled'
        self.save_accounts(accounts)

    def delete_account(self, user_id):
        accounts = self.get_all_accounts()
        # Remove state file
        acc = next((a for a in accounts if a['id'] == user_id), None)
        if acc and os.path.exists(acc['state_file']):
            try:
                os.remove(acc['state_file'])
            except:
                pass
        
        accounts = [a for a in accounts if a['id'] != user_id]
        self.save_accounts(accounts)

    def get_user_agent_for_session(self):
        return random.choice(USER_AGENTS)
