#!/usr/bin/env python3
import asyncio
import os
import json
import subprocess
import time
import shutil
import socks
import sys
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon import TelegramClient as AsyncClient
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = "7729368839:AAH1OWrXgzYUj-PFJIg0YN1Xo1FV3W1H1sQ"  # Replace with your actual bot token
MAIN_ADMIN_ID = 8055434763
MAIN_ADMIN_USERNAME = "@OrgJhonySins"

# ============================================
# INITIALIZE
# ============================================
# Initialize bot without starting it yet
bot = TelegramClient('orbit_master_session', 6, "eb06d4abfb49dc3eeb1aeb98ae0f581e")
worker_processes = {}
session_waiting = {}
user_waiting = {}
user_selection = {}
session_deletion = {}
user_session_pages = {}
parallel_session_data = {}

# ============================================
# UTILITY FUNCTIONS
# ============================================
def get_target():
    """Get target username from config"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        return config.get("target_user", "")
    except:
        return ""

def save_target(username):
    """Save target username to config"""
    try:
        with open("config.json", "w") as f:
            json.dump({"target_user": username}, f)
        return True
    except:
        return False

# ============================================
# SESSION GENERATOR CLASS
# ============================================
class SessionGenerator:
    def __init__(self):
        # Hardcoded proxy details
        self.PROXY_HOST = "154.219.4.151"
        self.PROXY_PORT = 63291
        self.PROXY_USERNAME = "qXAdZHbf"
        self.PROXY_PASSWORD = "ayr1bGWq"
        self.proxy_config = (socks.SOCKS5, self.PROXY_HOST, self.PROXY_PORT, 
                            True, self.PROXY_USERNAME, self.PROXY_PASSWORD)
    
    async def generate_session_parallel(self, api_id, api_hash, phone_number, user_id=None):
        """Generate session in parallel mode"""
        try:
            print(f"[PARALLEL] Starting session generation for {phone_number}")
            
            async with AsyncClient(
                StringSession(), 
                int(api_id), 
                api_hash,
                proxy=self.proxy_config
            ) as client:
                await client.connect()
                
                if not await client.is_user_authorized():
                    try:
                        print(f"[PARALLEL] Sending OTP to {phone_number}...")
                        
                        sent_code = await client.send_code_request(phone_number)
                        print(f"[PARALLEL] OTP sent to {phone_number}")
                        
                        return {
                            "status": "needs_otp",
                            "phone": phone_number,
                            "api_id": api_id,
                            "api_hash": api_hash,
                            "client": client,
                            "sent_code": sent_code,
                            "proxy_used": True
                        }
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"[PARALLEL] Login error for {phone_number}: {error_msg}")
                        
                        return {
                            "status": "failed",
                            "phone": phone_number,
                            "error": error_msg
                        }
                
                # Already authorized, get session string
                string_session = client.session.save()
                print(f"[PARALLEL] ✅ Session ready for {phone_number}")
                
                return {
                    "status": "success",
                    "phone": phone_number,
                    "api_id": api_id,
                    "api_hash": api_hash,
                    "string_session": string_session,
                    "proxy_used": True
                }
                
        except Exception as e:
            print(f"[PARALLEL] Critical error for {phone_number}: {str(e)}")
            return {
                "status": "failed",
                "phone": phone_number,
                "error": str(e)
            }
    
    async def process_otp(self, client, phone_number, sent_code, otp_code, password=None):
        """Process OTP for parallel session generation"""
        try:
            print(f"[PARALLEL] Processing OTP for {phone_number}")
            
            # Sign in with OTP
            await client.sign_in(phone_number, otp_code, phone_code_hash=sent_code.phone_code_hash)
            
            # Check if 2FA is needed
            if password:
                print(f"[PARALLEL] Processing 2FA for {phone_number}")
                await client.sign_in(password=password)
            
            # Get session string
            string_session = client.session.save()
            print(f"[PARALLEL] ✅ Session generated for {phone_number}")
            
            return {
                "status": "success",
                "phone": phone_number,
                "string_session": string_session
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[PARALLEL] OTP processing failed: {error_msg}")
            
            # Check if 2FA is needed
            if "password" in error_msg.lower():
                return {
                    "status": "needs_2fa",
                    "phone": phone_number,
                    "error": "2FA password required"
                }
            
            return {
                "status": "failed",
                "phone": phone_number,
                "error": error_msg
            }

# Create session generator instance
session_generator = SessionGenerator()

# ============================================
# SETUP FOLDERS
# ============================================
def setup_folders():
    folders = ["logs", "users", "admin_tdata"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    if not os.path.exists("config.json"):
        with open("config.json", "w") as f:
            json.dump({"target_user": ""}, f)
    
    if not os.path.exists("allowed_users.json"):
        initial_data = {
            "admins": [MAIN_ADMIN_ID],
            "users": [],
            "usernames": {},
            "user_folders": {},
            "user_limits": {}
        }
        with open("allowed_users.json", "w") as f:
            json.dump(initial_data, f, indent=2)
    else:
        try:
            with open("allowed_users.json", "r") as f:
                data = json.load(f)
            
            if "user_limits" not in data:
                data["user_limits"] = {}
            if "user_folders" not in data:
                data["user_folders"] = {}
            
            with open("allowed_users.json", "w") as f:
                json.dump(data, f, indent=2)
        except:
            pass

# ============================================
# USER FUNCTIONS
# ============================================
def is_admin(user_id):
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        user_id_str = str(user_id)
        admin_ids = [str(admin) for admin in data.get("admins", [])]
        return user_id_str in admin_ids
    except:
        return str(user_id) == str(MAIN_ADMIN_ID)

def is_allowed_user(user_id):
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        user_id_str = str(user_id)
        admin_ids = [str(admin) for admin in data.get("admins", [])]
        user_ids = [str(user) for user in data.get("users", [])]
        return user_id_str in admin_ids or user_id_str in user_ids
    except:
        return str(user_id) == str(MAIN_ADMIN_ID)

def add_allowed_user(user_id, username):
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        user_id_str = str(user_id)
        
        if user_id_str in [str(uid) for uid in data["users"]]:
            data["usernames"][user_id_str] = username
        else:
            data["users"].append(user_id)
            data["usernames"][user_id_str] = username
            data["user_folders"][user_id_str] = f"user_{user_id}_tdata"
            data["user_limits"][user_id_str] = {
                "max_sessions": 10,
                "can_run_ads": True,
                "ads_running": False
            }
            os.makedirs(f"users/user_{user_id}_tdata", exist_ok=True)
        
        with open("allowed_users.json", "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

def update_user_limits(user_id, max_sessions=None, can_run_ads=None):
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        user_id_str = str(user_id)
        
        if user_id_str in data["user_limits"]:
            if max_sessions is not None:
                data["user_limits"][user_id_str]["max_sessions"] = max_sessions
            if can_run_ads is not None:
                data["user_limits"][user_id_str]["can_run_ads"] = can_run_ads
        else:
            data["user_limits"][user_id_str] = {
                "max_sessions": max_sessions or 10,
                "can_run_ads": can_run_ads or True,
                "ads_running": False
            }
        
        with open("allowed_users.json", "w") as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

def get_user_limits(user_id):
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        user_id_str = str(user_id)
        
        if is_admin(user_id):
            return {
                "max_sessions": 999,
                "can_run_ads": True,
                "ads_running": False,
                "current_sessions": count_user_accounts(user_id)
            }
        
        if user_id_str in data["user_limits"]:
            limits = data["user_limits"][user_id_str].copy()
            limits["current_sessions"] = count_user_accounts(user_id)
            return limits
        else:
            return {
                "max_sessions": 10,
                "can_run_ads": True,
                "ads_running": False,
                "current_sessions": count_user_accounts(user_id)
            }
    except:
        return {
            "max_sessions": 10,
            "can_run_ads": True,
            "ads_running": False,
            "current_sessions": 0
        }

def get_all_users_with_info():
    """Get all users with their info for selection"""
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        users = []
        for user_id in data.get("users", []):
            user_id_str = str(user_id)
            username = data["usernames"].get(user_id_str, "Unknown")
            limits = data["user_limits"].get(user_id_str, {})
            current_sessions = count_user_accounts(user_id)
            
            users.append({
                "id": user_id,
                "username": username,
                "max_sessions": limits.get("max_sessions", 10),
                "can_run_ads": limits.get("can_run_ads", True),
                "current_sessions": current_sessions
            })
        
        return users
    except:
        return []

def get_user_folder(user_id):
    if is_admin(user_id):
        return "admin_tdata"
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        user_id_str = str(user_id)
        if user_id_str in data.get("user_folders", {}):
            return f"users/{data['user_folders'][user_id_str]}"
    except:
        pass
    folder = f"users/user_{user_id}_tdata"
    os.makedirs(folder, exist_ok=True)
    return folder

def count_user_accounts(user_id):
    folder = get_user_folder(user_id)
    count = 0
    if os.path.exists(folder):
        for file in os.listdir(folder):
            if file.startswith("session") and file.endswith(".json"):
                count += 1
    return count

def can_user_add_more_sessions(user_id):
    limits = get_user_limits(user_id)
    current = count_user_accounts(user_id)
    return current < limits["max_sessions"]

def add_user_session(user_id, session_data):
    if not can_user_add_more_sessions(user_id):
        return False, "Session limit reached"
    
    try:
        folder = get_user_folder(user_id)
        os.makedirs(folder, exist_ok=True)
        
        existing = count_user_accounts(user_id)
        num = existing + 1
        
        filename = f"{folder}/session{num}.json"
        with open(filename, "w") as f:
            json.dump(session_data, f, indent=2)
        
        return True, f"Session {num} added"
    except Exception as e:
        return False, str(e)

def get_user_sessions(user_id):
    """Get list of session files for a user"""
    folder = get_user_folder(user_id)
    sessions = []
    if os.path.exists(folder):
        files = sorted([f for f in os.listdir(folder) if f.startswith("session") and f.endswith(".json")],
                      key=lambda x: int(x.replace("session", "").replace(".json", "")) if x.replace("session", "").replace(".json", "").isdigit() else 999)
        
        for file in files:
            filepath = os.path.join(folder, file)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    sessions.append({
                        "filename": file,
                        "filepath": filepath,
                        "api_id": data.get("api_id"),
                        "created": os.path.getctime(filepath)
                    })
            except:
                sessions.append({
                    "filename": file,
                    "filepath": filepath,
                    "api_id": "Unknown",
                    "created": os.path.getctime(filepath)
                })
    
    return sessions

def delete_user_session(user_id, session_filename):
    """Delete a specific session file for a user"""
    try:
        folder = get_user_folder(user_id)
        filepath = os.path.join(folder, session_filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            
            # Rename remaining sessions to maintain sequential order
            sessions = get_user_sessions(user_id)
            
            # Create temporary copies
            temp_files = []
            for i, session in enumerate(sessions, 1):
                old_path = session["filepath"]
                temp_path = f"{old_path}.temp{i}"
                shutil.copy2(old_path, temp_path)
                temp_files.append(temp_path)
            
            # Delete all original files
            for session in sessions:
                if os.path.exists(session["filepath"]):
                    os.remove(session["filepath"])
            
            # Create new sequential files from temp files
            for i, temp_file in enumerate(temp_files, 1):
                new_filename = f"session{i}.json"
                new_path = os.path.join(folder, new_filename)
                shutil.copy2(temp_file, new_path)
                os.remove(temp_file)
            
            return True, f"Session deleted and reordered"
        else:
            return False, "Session file not found"
    except Exception as e:
        return False, str(e)

def delete_all_user_sessions(user_id):
    """Delete all sessions for a user"""
    try:
        folder = get_user_folder(user_id)
        if os.path.exists(folder):
            # Delete all session files
            deleted_count = 0
            for file in os.listdir(folder):
                if file.startswith("session") and file.endswith(".json"):
                    os.remove(os.path.join(folder, file))
                    deleted_count += 1
            
            return True, f"Deleted {deleted_count} sessions"
        else:
            return False, "User folder not found"
    except Exception as e:
        return False, str(e)

# ============================================
# WORKER MANAGEMENT - FIXED
# ============================================
def start_user_worker(user_id):
    """Start ads worker for specific user"""
    global worker_processes
    
    # First, ensure any existing worker is stopped
    stop_user_worker(user_id)
    
    try:
        # Check if user can run ads
        limits = get_user_limits(user_id)
        if not limits.get("can_run_ads", True):
            return False, "User not allowed to run ads"
        
        # Start worker with user_id as argument
        print(f"🚀 Starting worker for user {user_id}...")
        
        # FIXED: Use sys.executable instead of "python"
        process = subprocess.Popen([sys.executable, "ad_worker.py", str(user_id)])
        worker_processes[user_id] = process
        
        # Wait a moment to see if process starts
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is not None:
            return False, "Worker failed to start"
        
        print(f"✅ Worker started for user {user_id}, PID: {process.pid}")
        return True, "Ads started successfully"
    except Exception as e:
        print(f"❌ Error starting worker for user {user_id}: {e}")
        return False, str(e)

def stop_user_worker(user_id):
    """Stop ads worker for specific user"""
    global worker_processes
    
    try:
        # Method 1: Send stop signal via file
        stop_file = f"stop_worker_{user_id}.txt"
        with open(stop_file, "w") as f:
            f.write("stop")
        
        print(f"🛑 Sent stop signal to user {user_id}")
        time.sleep(3)  # Give time to stop
        
        # Method 2: Terminate process if still running
        if user_id in worker_processes and worker_processes[user_id] is not None:
            process = worker_processes[user_id]
            if process.poll() is None:  # Still running
                print(f"⚠️ Force terminating process for user {user_id}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
            
            worker_processes[user_id] = None
        
        # Clean up stop file
        if os.path.exists(stop_file):
            os.remove(stop_file)
        
        # Also check general stop file
        if os.path.exists("stop_worker.txt"):
            os.remove("stop_worker.txt")
        
        print(f"✅ Worker stopped for user {user_id}")
        return True, "Ads stopped"
    except Exception as e:
        print(f"⚠️ Error stopping worker for user {user_id}: {e}")
        return True, "Ads stopped"

def is_user_worker_running(user_id):
    """Check if user's worker is running"""
    global worker_processes
    
    # First check if process exists and is not None
    if user_id not in worker_processes or worker_processes[user_id] is None:
        return False
    
    # Check if process is still running
    process = worker_processes[user_id]
    return process.poll() is None

def cleanup_workers():
    """Clean up any dead worker processes"""
    global worker_processes
    dead_users = []
    
    for user_id, process in worker_processes.items():
        if process is not None and process.poll() is not None:
            dead_users.append(user_id)
    
    for user_id in dead_users:
        worker_processes[user_id] = None
    
    if dead_users:
        print(f"🧹 Cleaned up {len(dead_users)} dead workers")

# ============================================
# START COMMAND
# ============================================
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    
    # Clean up any dead workers first
    cleanup_workers()
    
    # Clear waiting states
    if user_id in user_waiting:
        del user_waiting[user_id]
    if user_id in session_waiting:
        del session_waiting[user_id]
    if user_id in user_selection:
        del user_selection[user_id]
    if user_id in session_deletion:
        del session_deletion[user_id]
    if user_id in user_session_pages:
        del user_session_pages[user_id]
    if user_id in parallel_session_data:
        del parallel_session_data[user_id]
    
    if not is_allowed_user(user_id):
        await event.reply("❌ Unauthorized!")
        return
    
    user_accounts = count_user_accounts(user_id)
    target = get_target()
    worker_running = is_user_worker_running(user_id)
    status = "🟢 RUNNING" if worker_running else "🔴 STOPPED"
    limits = get_user_limits(user_id)
    
    if is_admin(user_id):
        account_text = f"📱 Accounts: {user_accounts}\n"
    else:
        account_text = f"📱 Your Accounts: {user_accounts}/{limits['max_sessions']}\n"
    
    buttons = []
    
    if limits.get("can_run_ads", True):
        if worker_running:
            buttons.append([Button.inline("🛑 STOP MY ADS", b"stop_my_ads")])
        else:
            buttons.append([Button.inline("🚀 START MY ADS", b"start_my_ads")])
    
    buttons.append([
        Button.inline("🎯 SET TARGET", b"set_target"), 
        Button.inline("📊 STATUS", b"status")
    ])
    
    buttons.append([
        Button.inline("👤 MY ACCOUNTS", b"account_tools"), 
        Button.inline("⚙️ SETTINGS", b"settings")
    ])
    
    if is_admin(user_id):
        buttons.append([Button.inline("👥 USER MANAGER", b"user_manager")])
    
    await event.reply(
        f"🤖 **ORBIT MASTER**\n\n"
        f"👤 You: {'👑 ADMIN' if is_admin(user_id) else '👤 USER'}\n"
        f"{account_text}"
        f"🎯 Target: @{target if target else 'Not set'}\n"
        f"⚡ Ads Status: {status}\n"
        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}",
        buttons=buttons
    )

# ============================================
# ACCOUNT MANAGEMENT
# ============================================
@bot.on(events.CallbackQuery(data=b"account_tools"))
async def account_tools_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    user_accounts = count_user_accounts(user_id)
    limits = get_user_limits(user_id)
    can_add = can_user_add_more_sessions(user_id)
    
    buttons = []
    
    if can_add:
        buttons.append([
            Button.inline("➕ ADD SINGLE SESSION", b"add_sessions"),
            Button.inline("🚀 ADD PARALLEL SESSIONS", b"parallel_sessions")
        ])
    else:
        buttons.append([Button.inline("❌ LIMIT REACHED", b"limit_reached")])
    
    if user_accounts > 0:
        buttons.append([Button.inline("🗑️ DELETE SESSIONS", b"delete_sessions")])
        buttons.append([Button.inline("🗑️ DELETE ALL SESSIONS", b"delete_all_sessions_confirm")])
    
    buttons.append([Button.inline(f"📁 MY SESSIONS ({user_accounts}/{limits['max_sessions']})", b"list_sessions")])
    buttons.append([Button.inline("🔙 BACK", b"back_main")])
    
    msg = f"👤 YOUR ACCOUNTS\n\n"
    msg += f"Sessions: {user_accounts}/{limits['max_sessions']}\n"
    msg += f"Ads Permission: {'✅ Yes' if limits['can_run_ads'] else '❌ No'}\n\n"
    msg += f"**New Feature:** 🚀 Parallel Session Generation\n"
    msg += f"Add multiple accounts simultaneously!"
    
    await event.edit(msg, buttons=buttons)

# ============================================
# DELETE SESSIONS
# ============================================
@bot.on(events.CallbackQuery(data=b"delete_sessions"))
async def delete_sessions_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    sessions = get_user_sessions(user_id)
    
    if not sessions:
        await event.answer("❌ No sessions to delete!", alert=True)
        return
    
    # Store sessions for pagination
    user_session_pages[user_id] = {
        "sessions": sessions,
        "page": 1,
        "per_page": 8
    }
    
    await show_session_selection_page(event, user_id)

async def show_session_selection_page(event, user_id, page=1):
    """Show a page of session selection buttons"""
    if user_id not in user_session_pages:
        await event.answer("❌ Session data expired!", alert=True)
        return
    
    sessions_data = user_session_pages[user_id]
    sessions = sessions_data["sessions"]
    per_page = sessions_data["per_page"]
    total_pages = (len(sessions) + per_page - 1) // per_page
    
    # Calculate start and end indices
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(sessions))
    
    # Create buttons for sessions on this page
    buttons = []
    for i in range(start_idx, end_idx):
        session = sessions[i]
        api_id = session["api_id"] or "Unknown"
        if isinstance(api_id, int):
            api_id = str(api_id)[:6]
        # Clean filename for callback data
        safe_filename = session['filename'].replace('.', '_')
        button_text = f"🗑️ {session['filename']} (API: {api_id})"
        callback_data = f"del_{safe_filename}"
        buttons.append([Button.inline(button_text, callback_data.encode())])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(Button.inline("⬅️ PREV", f"page_{page-1}".encode()))
    
    nav_buttons.append(Button.inline(f"📄 {page}/{total_pages}", b"current_page"))
    
    if page < total_pages:
        nav_buttons.append(Button.inline("NEXT ➡️", f"page_{page+1}".encode()))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([Button.inline("🔙 BACK", b"account_tools")])
    
    await event.edit(
        f"🗑️ SELECT SESSION TO DELETE\n\n"
        f"Page {page} of {total_pages}\n"
        f"Total sessions: {len(sessions)}\n"
        f"Click on a session to delete it:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(pattern=b"page_"))
async def session_page_callback(event):
    """Handle pagination for session selection"""
    user_id = event.sender_id
    
    if user_id not in user_session_pages:
        await event.answer("❌ Session data expired!", alert=True)
        return
    
    try:
        # Get page number from callback data
        callback_data = event.data.decode()
        page = int(callback_data.split("_")[1])
        
        await show_session_selection_page(event, user_id, page)
    except:
        await event.answer("❌ Invalid page!", alert=True)

@bot.on(events.CallbackQuery(pattern=b"del_"))
async def delete_session_select_callback(event):
    """Handle session selection for deletion"""
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    try:
        # Extract filename from callback data
        callback_data = event.data.decode()
        safe_filename = callback_data.split("_", 1)[1]
        # Convert back to original filename
        filename = safe_filename.replace('_', '.')
        
        # Verify the file exists
        sessions = get_user_sessions(user_id)
        session_exists = any(s["filename"] == filename for s in sessions)
        
        if not session_exists:
            await event.answer("❌ Session not found!", alert=True)
            return
        
        # Store deletion info
        session_deletion[user_id] = {
            "filename": filename,
            "confirmed": False
        }
        
        # Ask for confirmation
        buttons = [
            [Button.inline("✅ YES, DELETE", b"confirm_delete_session")],
            [Button.inline("❌ NO, CANCEL", b"cancel_delete_session")]
        ]
        
        await event.edit(
            f"⚠️ CONFIRM DELETION\n\n"
            f"Session: {filename}\n"
            f"Are you sure you want to delete this session?",
            buttons=buttons
        )
        
    except Exception as e:
        print(f"Error in delete_session_select_callback: {e}")
        await event.answer("❌ Error selecting session!", alert=True)

@bot.on(events.CallbackQuery(data=b"confirm_delete_session"))
async def confirm_delete_session_callback(event):
    user_id = event.sender_id
    
    if user_id not in session_deletion:
        await event.answer("❌ No session selected!", alert=True)
        return
    
    filename = session_deletion[user_id]["filename"]
    
    # Delete the session
    success, message = delete_user_session(user_id, filename)
    
    if success:
        # Clear deletion state
        del session_deletion[user_id]
        
        # Get updated session count
        current = count_user_accounts(user_id)
        limits = get_user_limits(user_id)
        
        await event.edit(
            f"✅ SESSION DELETED\n\n"
            f"Deleted: {filename}\n"
            f"Remaining: {current}/{limits['max_sessions']} sessions"
        )
    else:
        await event.edit(f"❌ Failed to delete: {message}")
    
    # Return to account tools after delay
    await asyncio.sleep(3)
    await account_tools_callback(event)

@bot.on(events.CallbackQuery(data=b"cancel_delete_session"))
async def cancel_delete_session_callback(event):
    user_id = event.sender_id
    
    if user_id in session_deletion:
        del session_deletion[user_id]
    
    await event.answer("❌ Deletion cancelled", alert=True)
    await account_tools_callback(event)

@bot.on(events.CallbackQuery(data=b"delete_all_sessions_confirm"))
async def delete_all_sessions_confirm_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    current = count_user_accounts(user_id)
    
    if current == 0:
        await event.answer("❌ No sessions to delete!", alert=True)
        return
    
    buttons = [
        [Button.inline("✅ YES, DELETE ALL", b"delete_all_sessions")],
        [Button.inline("❌ NO, CANCEL", b"account_tools")]
    ]
    
    await event.edit(
        f"⚠️ CONFIRM DELETE ALL SESSIONS\n\n"
        f"This will delete ALL {current} sessions!\n"
        f"• All session files will be removed\n"
        f"• Ads will be stopped if running\n"
        f"• This action cannot be undone\n\n"
        f"Are you sure?",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(data=b"delete_all_sessions"))
async def delete_all_sessions_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    # Stop ads if running
    if is_user_worker_running(user_id):
        stop_user_worker(user_id)
        await asyncio.sleep(2)
    
    # Delete all sessions
    success, message = delete_all_user_sessions(user_id)
    
    if success:
        await event.edit(
            f"✅ ALL SESSIONS DELETED\n\n"
            f"{message}\n"
            f"You can now add new sessions."
        )
    else:
        await event.edit(f"❌ Failed: {message}")
    
    # Return to account tools after delay
    await asyncio.sleep(3)
    await account_tools_callback(event)

@bot.on(events.CallbackQuery(data=b"list_sessions"))
async def list_sessions_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    sessions = get_user_sessions(user_id)
    limits = get_user_limits(user_id)
    
    if sessions:
        msg = f"📁 YOUR SESSIONS ({len(sessions)}/{limits['max_sessions']})\n\n"
        for i, session in enumerate(sessions[:15], 1):
            api_id = session["api_id"] or "Unknown"
            if isinstance(api_id, int):
                api_id = str(api_id)[:6]
            created = datetime.fromtimestamp(session["created"]).strftime('%Y-%m-%d')
            msg += f"{i}. {session['filename']}\n"
            msg += f"   API: {api_id} | Created: {created}\n\n"
        
        if len(sessions) > 15:
            msg += f"... +{len(sessions)-15} more sessions"
    else:
        msg = "📁 No sessions found"
    
    buttons = [[Button.inline("🔙 BACK", b"account_tools")]]
    await event.edit(msg, buttons=buttons)

# ============================================
# USER MANAGER
# ============================================
@bot.on(events.CallbackQuery(data=b"user_manager"))
async def user_manager_callback(event):
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    buttons = [
        [Button.inline("➕ ADD USER", b"add_user")],
        [Button.inline("👥 SELECT USER TO MANAGE", b"show_users")],
        [Button.inline("📋 VIEW ALL USERS", b"view_all_users")],
        [Button.inline("🔙 BACK", b"back_main")]
    ]
    
    await event.edit("👥 USER MANAGER\n\nChoose an action:", buttons=buttons)

@bot.on(events.CallbackQuery(data=b"show_users"))
async def show_users_callback(event):
    """Show list of users to select"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    users = get_all_users_with_info()
    
    if not users:
        await event.edit("❌ No users found. Add users first.")
        return
    
    # Create buttons for user selection
    buttons = []
    for user in users:
        username = user["username"][:15] if len(user["username"]) > 15 else user["username"]
        button_text = f"👤 {username} ({user['current_sessions']}/{user['max_sessions']})"
        callback_data = f"manage_{user['id']}"
        buttons.append([Button.inline(button_text, callback_data.encode())])
    
    buttons.append([Button.inline("🔙 BACK", b"user_manager")])
    
    await event.edit(
        "👥 SELECT USER\n\n"
        "Click on a user to manage their settings:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(pattern=b"manage_"))
async def manage_user_callback(event):
    """Handle user selection"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    # Extract selected user ID from callback data
    try:
        callback_data = event.data.decode()
        selected_user_id = int(callback_data.split("_")[1])
    except:
        await event.answer("❌ Invalid selection!", alert=True)
        return
    
    # Store selection
    user_selection[user_id] = {
        "selected_user": selected_user_id,
        "action": "manage_user"
    }
    
    # Get user info
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        selected_id_str = str(selected_user_id)
        username = data["usernames"].get(selected_id_str, "Unknown")
        limits = data["user_limits"].get(selected_id_str, {})
        current_sessions = count_user_accounts(selected_user_id)
        
        # Check if user's ads are running
        ads_running = is_user_worker_running(selected_user_id)
        
        buttons = [
            [Button.inline("⚙️ SET SESSION LIMIT", b"set_session_limit")],
            [Button.inline(f"{'✅' if limits.get('can_run_ads', True) else '❌'} TOGGLE ADS PERMISSION", b"toggle_ads_permission")],
            [Button.inline("🗑️ MANAGE USER SESSIONS", b"manage_user_sessions")],
            [Button.inline("🔄 VIEW CURRENT SETTINGS", b"view_user_settings")],
        ]
        
        # Add start/stop ads button if user has permission
        if limits.get("can_run_ads", True):
            if ads_running:
                buttons.append([Button.inline("🛑 STOP USER ADS", b"stop_user_ads")])
            else:
                buttons.append([Button.inline("🚀 START USER ADS", b"start_user_ads")])
        
        buttons.append([Button.inline("🗑️ REMOVE USER", b"remove_user_confirm")])
        buttons.append([Button.inline("🔙 BACK TO USER LIST", b"show_users")])
        
        await event.edit(
            f"👤 MANAGING USER\n\n"
            f"Username: {username}\n"
            f"User ID: {selected_user_id}\n"
            f"Current Sessions: {current_sessions}\n"
            f"Session Limit: {limits.get('max_sessions', 10)}\n"
            f"Can Run Ads: {'✅ Yes' if limits.get('can_run_ads', True) else '❌ No'}\n"
            f"Ads Running: {'🟢 Yes' if ads_running else '🔴 No'}\n\n"
            f"Choose action:",
            buttons=buttons
        )
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@bot.on(events.CallbackQuery(data=b"manage_user_sessions"))
async def manage_user_sessions_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get user sessions
    sessions = get_user_sessions(selected_user_id)
    
    # Get username
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        username = data["usernames"].get(str(selected_user_id), "Unknown")
    except:
        username = "Unknown"
    
    if not sessions:
        buttons = [[Button.inline("🔙 BACK TO USER", b"back_to_user_manage")]]
        await event.edit(
            f"🗑️ MANAGE USER SESSIONS\n\n"
            f"User: {username} ({selected_user_id})\n"
            f"Total Sessions: 0\n\n"
            f"User has no sessions to manage.",
            buttons=buttons
        )
        return
    
    # Store sessions for pagination
    user_session_pages[admin_id] = {
        "sessions": sessions,
        "page": 1,
        "per_page": 8,
        "target_user": selected_user_id
    }
    
    await show_admin_session_selection_page(event, admin_id)

async def show_admin_session_selection_page(event, admin_id, page=1):
    """Show a page of session selection buttons for admin"""
    if admin_id not in user_session_pages:
        await event.answer("❌ Session data expired!", alert=True)
        return
    
    sessions_data = user_session_pages[admin_id]
    sessions = sessions_data["sessions"]
    target_user = sessions_data["target_user"]
    per_page = sessions_data["per_page"]
    total_pages = (len(sessions) + per_page - 1) // per_page
    
    # Calculate start and end indices
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(sessions))
    
    # Get username
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        username = data["usernames"].get(str(target_user), "Unknown")
    except:
        username = "Unknown"
    
    # Create buttons for sessions on this page
    buttons = []
    for i in range(start_idx, end_idx):
        session = sessions[i]
        api_id = session["api_id"] or "Unknown"
        if isinstance(api_id, int):
            api_id = str(api_id)[:6]
        # Clean filename for callback data
        safe_filename = session['filename'].replace('.', '_')
        button_text = f"🗑️ {session['filename']} (API: {api_id})"
        callback_data = f"adel_{target_user}_{safe_filename}"
        buttons.append([Button.inline(button_text, callback_data.encode())])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(Button.inline("⬅️ PREV", f"apage_{page-1}".encode()))
    
    nav_buttons.append(Button.inline(f"📄 {page}/{total_pages}", b"current_apage"))
    
    if page < total_pages:
        nav_buttons.append(Button.inline("NEXT ➡️", f"apage_{page+1}".encode()))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([Button.inline("🗑️ DELETE ALL SESSIONS", b"delete_all_user_sessions_confirm")])
    buttons.append([Button.inline("🔙 BACK TO USER", b"back_to_user_manage")])
    
    await event.edit(
        f"🗑️ DELETE USER SESSIONS\n\n"
        f"User: {username} ({target_user})\n"
        f"Page {page} of {total_pages}\n"
        f"Total sessions: {len(sessions)}\n"
        f"Select session to delete:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(pattern=b"apage_"))
async def admin_session_page_callback(event):
    """Handle pagination for admin session selection"""
    admin_id = event.sender_id
    
    if admin_id not in user_session_pages:
        await event.answer("❌ Session data expired!", alert=True)
        return
    
    try:
        # Get page number from callback data
        callback_data = event.data.decode()
        page = int(callback_data.split("_")[1])
        
        await show_admin_session_selection_page(event, admin_id, page)
    except:
        await event.answer("❌ Invalid page!", alert=True)

@bot.on(events.CallbackQuery(pattern=b"adel_"))
async def admin_delete_session_select_callback(event):
    """Handle admin session selection for deletion"""
    admin_id = event.sender_id
    
    if not is_admin(admin_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    try:
        # Extract user ID and filename from callback data
        callback_data = event.data.decode()
        parts = callback_data.split("_")
        target_user_id = int(parts[1])
        safe_filename = "_".join(parts[2:])
        
        # Convert back to original filename
        filename = safe_filename.replace('_', '.')
        
        # Verify the file exists
        sessions = get_user_sessions(target_user_id)
        session_exists = any(s["filename"] == filename for s in sessions)
        
        if not session_exists:
            await event.answer("❌ Session not found!", alert=True)
            return
        
        # Get username
        try:
            with open("allowed_users.json", "r") as f:
                data = json.load(f)
            username = data["usernames"].get(str(target_user_id), "Unknown")
        except:
            username = "Unknown"
        
        # Store deletion info
        session_deletion[admin_id] = {
            "target_user": target_user_id,
            "filename": filename,
            "username": username,
            "confirmed": False
        }
        
        # Ask for confirmation
        buttons = [
            [Button.inline("✅ YES, DELETE", b"admin_confirm_delete_session")],
            [Button.inline("❌ NO, CANCEL", b"admin_cancel_delete_session")]
        ]
        
        await event.edit(
            f"⚠️ CONFIRM SESSION DELETION\n\n"
            f"User: {username} ({target_user_id})\n"
            f"Session: {filename}\n\n"
            f"Are you sure you want to delete this session?",
            buttons=buttons
        )
        
    except Exception as e:
        print(f"Error in admin_delete_session_select_callback: {e}")
        await event.answer("❌ Error selecting session!", alert=True)

@bot.on(events.CallbackQuery(data=b"admin_confirm_delete_session"))
async def admin_confirm_delete_session_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in session_deletion:
        await event.answer("❌ No session selected!", alert=True)
        return
    
    target_user = session_deletion[admin_id]["target_user"]
    filename = session_deletion[admin_id]["filename"]
    username = session_deletion[admin_id]["username"]
    
    # Delete the session
    success, message = delete_user_session(target_user, filename)
    
    if success:
        # Clear deletion state
        del session_deletion[admin_id]
        
        # Get updated session count
        current = count_user_accounts(target_user)
        
        await event.edit(
            f"✅ SESSION DELETED\n\n"
            f"User: {username}\n"
            f"Deleted: {filename}\n"
            f"Remaining: {current} sessions"
        )
    else:
        await event.edit(f"❌ Failed to delete: {message}")
    
    # Return to session management after delay
    await asyncio.sleep(3)
    if admin_id in user_session_pages:
        # Refresh sessions list
        sessions = get_user_sessions(target_user)
        user_session_pages[admin_id]["sessions"] = sessions
        await show_admin_session_selection_page(event, admin_id, 1)
    else:
        await manage_user_sessions_callback(event)

@bot.on(events.CallbackQuery(data=b"admin_cancel_delete_session"))
async def admin_cancel_delete_session_callback(event):
    admin_id = event.sender_id
    
    if admin_id in session_deletion:
        del session_deletion[admin_id]
    
    await event.answer("❌ Deletion cancelled", alert=True)
    if admin_id in user_session_pages:
        await show_admin_session_selection_page(event, admin_id, 1)
    else:
        await manage_user_sessions_callback(event)

@bot.on(events.CallbackQuery(data=b"delete_all_user_sessions_confirm"))
async def delete_all_user_sessions_confirm_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    current = count_user_accounts(selected_user_id)
    
    if current == 0:
        await event.answer("❌ User has no sessions!", alert=True)
        return
    
    # Get username
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        username = data["usernames"].get(str(selected_user_id), "Unknown")
    except:
        username = "Unknown"
    
    buttons = [
        [Button.inline("✅ YES, DELETE ALL", b"delete_all_user_sessions_execute")],
        [Button.inline("❌ NO, CANCEL", b"manage_user_sessions")]
    ]
    
    await event.edit(
        f"⚠️ CONFIRM DELETE ALL SESSIONS\n\n"
        f"User: {username} ({selected_user_id})\n"
        f"This will delete ALL {current} sessions!\n"
        f"• All session files will be removed\n"
        f"• Ads will be stopped if running\n"
        f"• This action cannot be undone\n\n"
        f"Are you sure?",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(data=b"delete_all_user_sessions_execute"))
async def delete_all_user_sessions_execute_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get username
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        username = data["usernames"].get(str(selected_user_id), "Unknown")
    except:
        username = "Unknown"
    
    # Stop ads if running
    if is_user_worker_running(selected_user_id):
        stop_user_worker(selected_user_id)
        await asyncio.sleep(2)
    
    # Delete all sessions
    success, message = delete_all_user_sessions(selected_user_id)
    
    if success:
        await event.edit(
            f"✅ ALL SESSIONS DELETED\n\n"
            f"User: {username}\n"
            f"{message}"
        )
    else:
        await event.edit(f"❌ Failed: {message}")
    
    # Return to session management after delay
    await asyncio.sleep(3)
    await manage_user_sessions_callback(event)

@bot.on(events.CallbackQuery(data=b"back_to_user_manage"))
async def back_to_user_manage_callback(event):
    await manage_user_callback(event)

# ============================================
# PARALLEL SESSIONS
# ============================================
@bot.on(events.CallbackQuery(data=b"parallel_sessions"))
async def parallel_sessions_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    limits = get_user_limits(user_id)
    current = count_user_accounts(user_id)
    remaining = limits["max_sessions"] - current
    
    if remaining <= 0:
        await event.answer("❌ Session limit reached!", alert=True)
        return
    
    await event.delete()
    
    instructions = (
        "🚀 **PARALLEL SESSION GENERATOR**\n\n"
        f"You can add up to {remaining} more sessions.\n\n"
        "**Format (one account per line):**\n"
        "`API_ID`\n"
        "`API_HASH`\n"
        "`PHONE_NUMBER`\n"
        "`---` (separator)\n\n"
        "**Example:**\n"
        "1234567\n"
        "abc123def456ghi789\n"
        "+1234567890\n"
        "---\n"
        "7654321\n"
        "xyz789abc456def123\n"
        "+9876543210\n"
        "---\n\n"
        "Send multiple accounts for parallel generation!\n"
        "Each account will be processed simultaneously."
    )
    
    await event.respond(instructions)
    session_waiting[user_id] = {"step": "parallel_batch"}

async def process_parallel_sessions(user_id, accounts):
    """Process multiple sessions in parallel"""
    try:
        # Create progress message
        progress_msg = await bot.send_message(
            user_id,
            f"🔄 **Parallel Session Generation**\n"
            f"Total Accounts: {len(accounts)}\n"
            f"Processing: 0/{len(accounts)}\n"
            f"✅ Successful: 0\n"
            f"❌ Failed: 0\n"
            f"🔢 OTP Required: 0\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        results = []
        otp_required = []
        tasks = []
        
        # Create tasks for all accounts
        for i, account in enumerate(accounts):
            task = session_generator.generate_session_parallel(
                account['api_id'],
                account['api_hash'],
                account['phone'],
                user_id
            )
            tasks.append(task)
        
        # Run all tasks in parallel
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(parallel_results):
            if isinstance(result, Exception):
                results.append({
                    "phone": accounts[i].get('phone', f"Account_{i+1}"),
                    "status": "failed",
                    "error": str(result)
                })
            elif result.get("status") == "needs_otp":
                otp_required.append({
                    **result,
                    "index": i + 1,
                    "total": len(accounts)
                })
            else:
                results.append(result)
            
            # Update progress every 5 accounts
            if (i + 1) % 5 == 0 or (i + 1) == len(accounts):
                success_count = len([r for r in results if r.get("status") == "success"])
                failed_count = len([r for r in results if r.get("status") == "failed"])
                
                try:
                    await progress_msg.edit(
                        f"🔄 **Parallel Session Generation**\n"
                        f"Total Accounts: {len(accounts)}\n"
                        f"Processing: {i+1}/{len(accounts)}\n"
                        f"✅ Successful: {success_count}\n"
                        f"❌ Failed: {failed_count}\n"
                        f"🔢 OTP Required: {len(otp_required)}\n"
                        "━━━━━━━━━━━━━━━━━━━━"
                    )
                except:
                    pass
        
        # Store results
        parallel_session_data[user_id] = {
            "results": results,
            "otp_required": otp_required,
            "accounts": accounts,
            "progress_msg_id": progress_msg.id
        }
        
        # Show final results
        success_count = len([r for r in results if r.get("status") == "success"])
        failed_count = len([r for r in results if r.get("status") == "failed"])
        
        result_text = f"✅ **PARALLEL GENERATION COMPLETE**\n\n"
        result_text += f"📊 **Results:**\n"
        result_text += f"• ✅ Successful: {success_count}\n"
        result_text += f"• ❌ Failed: {failed_count}\n"
        result_text += f"• 🔢 OTP Required: {len(otp_required)}\n\n"
        
        if success_count > 0:
            result_text += "**Successful Accounts:**\n"
            for r in results:
                if r.get("status") == "success":
                    phone = r.get("phone", "Unknown")
                    result_text += f"• `{phone}`\n"
        
        buttons = []
        if success_count > 0:
            buttons.append([Button.inline("💾 ADD TO BOT", b"add_parallel_sessions")])
        
        if otp_required:
            buttons.append([Button.inline("🔢 ENTER OTPs", b"enter_otps")])
        
        buttons.append([Button.inline("🔄 RETRY FAILED", b"retry_failed")])
        buttons.append([Button.inline("📋 VIEW ALL RESULTS", b"view_parallel_results")])
        
        await progress_msg.edit(result_text, buttons=buttons)
        
    except Exception as e:
        await bot.send_message(user_id, f"❌ **Parallel Generation Error:**\n{str(e)}")

@bot.on(events.CallbackQuery(data=b"add_parallel_sessions"))
async def add_parallel_sessions_callback(event):
    user_id = event.sender_id
    
    if user_id not in parallel_session_data:
        await event.answer("❌ No session data found!", alert=True)
        return
    
    data = parallel_session_data[user_id]
    results = data["results"]
    
    # Filter only successful sessions
    successful_sessions = [r for r in results if r.get("status") == "success"]
    
    if not successful_sessions:
        await event.answer("❌ No successful sessions to add!", alert=True)
        return
    
    added_count = 0
    for session in successful_sessions:
        session_data = {
            "api_id": session.get("api_id"),
            "api_hash": session.get("api_hash"),
            "string_session": session.get("string_session"),
            "generated_at": datetime.now().isoformat(),
            "phone": session.get("phone"),
            "proxy_used": True
        }
        
        success, message = add_user_session(user_id, session_data)
        if success:
            added_count += 1
    
    # Update user limits
    current = count_user_accounts(user_id)
    limits = get_user_limits(user_id)
    
    await event.edit(
        f"✅ **Sessions Added Successfully**\n\n"
        f"• Added: {added_count} sessions\n"
        f"• Total: {current}/{limits['max_sessions']} sessions\n\n"
        f"You can now start ads with these sessions!"
    )

@bot.on(events.CallbackQuery(data=b"enter_otps"))
async def enter_otps_callback(event):
    user_id = event.sender_id
    
    if user_id not in parallel_session_data:
        await event.answer("❌ No OTP data found!", alert=True)
        return
    
    data = parallel_session_data[user_id]
    otp_accounts = data.get("otp_required", [])
    
    if not otp_accounts:
        await event.answer("✅ All OTPs already processed!", alert=True)
        return
    
    # Create OTP input interface
    buttons = []
    for i, acc in enumerate(otp_accounts[:10], 1):  # Show first 10
        phone = acc.get('phone', f"Account {i}")
        button_text = f"📱 {phone}"
        callback_data = f"otp_{i}"
        buttons.append([Button.inline(button_text, callback_data.encode())])
    
    if len(otp_accounts) > 10:
        buttons.append([Button.inline("📄 MORE ACCOUNTS", b"otp_page_2")])
    
    buttons.append([Button.inline("🔙 BACK", b"view_parallel_results")])
    
    await event.edit(
        "🔢 **ENTER OTPs**\n\n"
        f"{len(otp_accounts)} accounts need OTP verification\n"
        "Click on a phone number to enter OTP:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(pattern=b"otp_"))
async def handle_otp_input_callback(event):
    """Handle OTP input for parallel sessions"""
    user_id = event.sender_id
    
    if user_id not in parallel_session_data:
        await event.answer("❌ No OTP data found!", alert=True)
        return
    
    try:
        callback_data = event.data.decode()
        index = int(callback_data.split("_")[1]) - 1
        
        data = parallel_session_data[user_id]
        otp_accounts = data.get("otp_required", [])
        
        if index >= len(otp_accounts):
            await event.answer("❌ Invalid account!", alert=True)
            return
        
        account = otp_accounts[index]
        phone = account.get("phone", f"Account {index + 1}")
        
        await event.delete()
        await event.respond(
            f"🔢 **Enter OTP for:** `{phone}`\n\n"
            f"Send OTP code (6 digits):"
        )
        
        # Store OTP input state
        user_waiting[user_id] = {
            "action": "parallel_otp",
            "account_index": index,
            "phone": phone
        }
        
    except Exception as e:
        await event.answer(f"❌ Error: {str(e)}", alert=True)

@bot.on(events.CallbackQuery(data=b"retry_failed"))
async def retry_failed_callback(event):
    user_id = event.sender_id
    
    if user_id not in parallel_session_data:
        await event.answer("❌ No session data found!", alert=True)
        return
    
    data = parallel_session_data[user_id]
    results = data["results"]
    accounts = data["accounts"]
    
    # Filter failed accounts
    failed_indices = []
    for i, result in enumerate(results):
        if result.get("status") == "failed":
            failed_indices.append(i)
    
    if not failed_indices:
        await event.answer("✅ No failed accounts to retry!", alert=True)
        return
    
    # Retry failed accounts
    failed_accounts = [accounts[i] for i in failed_indices]
    await event.edit(f"🔄 Retrying {len(failed_accounts)} failed accounts...")
    
    # Process retry
    await process_parallel_sessions(user_id, failed_accounts)

@bot.on(events.CallbackQuery(data=b"view_parallel_results"))
async def view_parallel_results_callback(event):
    user_id = event.sender_id
    
    if user_id not in parallel_session_data:
        await event.answer("❌ No session data found!", alert=True)
        return
    
    data = parallel_session_data[user_id]
    results = data["results"]
    otp_accounts = data.get("otp_required", [])
    
    success_count = len([r for r in results if r.get("status") == "success"])
    failed_count = len([r for r in results if r.get("status") == "failed"])
    
    result_text = f"📊 **PARALLEL GENERATION RESULTS**\n\n"
    result_text += f"**Statistics:**\n"
    result_text += f"• ✅ Successful: {success_count}\n"
    result_text += f"• ❌ Failed: {failed_count}\n"
    result_text += f"• 🔢 OTP Required: {len(otp_accounts)}\n"
    result_text += f"• 📱 Total: {len(results)}\n\n"
    
    if success_count > 0:
        result_text += "**Successful Accounts:**\n"
        for i, r in enumerate(results[:10], 1):
            if r.get("status") == "success":
                phone = r.get("phone", f"Account {i}")
                result_text += f"• `{phone}`\n"
        
        if success_count > 10:
            result_text += f"• ... and {success_count - 10} more\n"
    
    buttons = []
    if success_count > 0:
        buttons.append([Button.inline("💾 ADD TO BOT", b"add_parallel_sessions")])
    
    if otp_accounts:
        buttons.append([Button.inline("🔢 ENTER OTPs", b"enter_otps")])
    
    buttons.append([Button.inline("🔄 RETRY FAILED", b"retry_failed")])
    buttons.append([Button.inline("🔙 BACK", b"account_tools")])
    
    await event.edit(result_text, buttons=buttons)

# ============================================
# OTHER CALLBACKS
# ============================================
@bot.on(events.CallbackQuery(data=b"add_sessions"))
async def add_sessions_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    if not can_user_add_more_sessions(user_id):
        await event.answer("❌ Limit reached!", alert=True)
        return
    
    limits = get_user_limits(user_id)
    current = count_user_accounts(user_id)
    remaining = limits["max_sessions"] - current
    
    await event.delete()
    await event.respond(f"Send number of sessions to add (1-{remaining}):")
    session_waiting[user_id] = {"step": "waiting_count"}

@bot.on(events.CallbackQuery(data=b"start_my_ads"))
async def start_my_ads_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    limits = get_user_limits(user_id)
    if not limits["can_run_ads"]:
        await event.answer("❌ Ads permission denied!", alert=True)
        return
    
    user_accounts = count_user_accounts(user_id)
    target = get_target()
    
    if user_accounts == 0:
        await event.edit("❌ No sessions!")
        return
    
    if not target:
        await event.edit("❌ No target!")
        return
    
    await event.edit("🚀 Starting ads...")
    success, message = start_user_worker(user_id)
    
    if success:
        await event.edit(f"✅ ADS STARTED!\nAccounts: {user_accounts}\nTarget: @{target}")
    else:
        await event.edit(f"❌ {message}")

@bot.on(events.CallbackQuery(data=b"stop_my_ads"))
async def stop_my_ads_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    await event.edit("🛑 Stopping ads...")
    success, message = stop_user_worker(user_id)
    
    if success:
        await event.edit("✅ ADS STOPPED!")
    else:
        await event.edit(f"❌ {message}")

@bot.on(events.CallbackQuery(data=b"set_target"))
async def set_target_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    await event.delete()
    await event.respond("🎯 Send target username:")

@bot.on(events.CallbackQuery(data=b"status"))
async def status_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    user_accounts = count_user_accounts(user_id)
    target = get_target()
    worker_running = is_user_worker_running(user_id)
    status = "🟢 RUNNING" if worker_running else "🔴 STOPPED"
    limits = get_user_limits(user_id)
    
    msg = f"📊 STATUS\n\n"
    msg += f"Accounts: {user_accounts}/{limits['max_sessions']}\n"
    msg += f"Target: @{target}\n"
    msg += f"Ads Status: {status}\n"
    msg += f"Ads Permission: {'✅ Yes' if limits['can_run_ads'] else '❌ No'}"
    
    await event.edit(msg)

@bot.on(events.CallbackQuery(data=b"settings"))
async def settings_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    limits = get_user_limits(user_id)
    
    msg = f"⚙️ YOUR SETTINGS\n\n"
    msg += f"Session Limit: {limits['max_sessions']}\n"
    msg += f"Current: {limits['current_sessions']}\n"
    msg += f"Can Run Ads: {'✅ Yes' if limits['can_run_ads'] else '❌ No'}"
    
    buttons = [[Button.inline("🔙 BACK", b"back_main")]]
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"limit_reached"))
async def limit_reached_callback(event):
    user_id = event.sender_id
    limits = get_user_limits(user_id)
    
    await event.answer(
        f"❌ Limit reached!\n"
        f"You have {limits['current_sessions']}/{limits['max_sessions']} sessions.\n"
        f"Contact admin to increase limit.",
        alert=True
    )

@bot.on(events.CallbackQuery(data=b"set_session_limit"))
async def set_session_limit_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get current username
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        username = data["usernames"].get(str(selected_user_id), "Unknown")
    except:
        username = "Unknown"
    
    await event.delete()
    await event.respond(
        f"⚙️ SET SESSION LIMIT\n\n"
        f"User: {username} ({selected_user_id})\n\n"
        f"Enter new session limit (1-100):"
    )
    user_waiting[admin_id] = {"action": "set_limit", "target_user": selected_user_id}

@bot.on(events.CallbackQuery(data=b"toggle_ads_permission"))
async def toggle_ads_permission_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get current settings
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        selected_id_str = str(selected_user_id)
        username = data["usernames"].get(selected_id_str, "Unknown")
        current_ads = data["user_limits"].get(selected_id_str, {}).get("can_run_ads", True)
        new_ads = not current_ads
        
        # Update permission
        if selected_id_str in data["user_limits"]:
            data["user_limits"][selected_id_str]["can_run_ads"] = new_ads
        else:
            data["user_limits"][selected_id_str] = {"can_run_ads": new_ads, "max_sessions": 10}
        
        with open("allowed_users.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # If revoking ads permission, stop any running ads
        if not new_ads and is_user_worker_running(selected_user_id):
            stop_user_worker(selected_user_id)
        
        status = "✅ GRANTED" if new_ads else "❌ REVOKED"
        await event.edit(
            f"🔄 ADS PERMISSION UPDATED\n\n"
            f"User: {username}\n"
            f"Permission: {status}\n\n"
            f"User can {'now' if new_ads else 'no longer'} run ads."
        )
        
        # Update the management view
        await asyncio.sleep(2)
        await manage_user_callback(event)
        
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@bot.on(events.CallbackQuery(data=b"start_user_ads"))
async def start_user_ads_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get user info
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        selected_id_str = str(selected_user_id)
        username = data["usernames"].get(selected_id_str, "Unknown")
        limits = data["user_limits"].get(selected_id_str, {})
        
        if not limits.get("can_run_ads", True):
            await event.answer("❌ User doesn't have ads permission!", alert=True)
            return
        
        user_accounts = count_user_accounts(selected_user_id)
        target = get_target()
        
        if user_accounts == 0:
            await event.answer("❌ User has no sessions!", alert=True)
            return
        
        if not target:
            await event.answer("❌ No target set!", alert=True)
            return
        
        await event.edit(f"🚀 Starting ads for {username}...")
        
        success, message = start_user_worker(selected_user_id)
        
        if success:
            await event.edit(
                f"✅ ADS STARTED FOR USER\n\n"
                f"User: {username}\n"
                f"Accounts: {user_accounts}\n"
                f"Target: @{target}\n"
                f"Status: 🟢 RUNNING"
            )
        else:
            await event.edit(f"❌ Failed: {message}")
        
        # Return to user management after delay
        await asyncio.sleep(3)
        await manage_user_callback(event)
        
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@bot.on(events.CallbackQuery(data=b"stop_user_ads"))
async def stop_user_ads_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get user info
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        selected_id_str = str(selected_user_id)
        username = data["usernames"].get(selected_id_str, "Unknown")
        
        await event.edit(f"🛑 Stopping ads for {username}...")
        
        success, message = stop_user_worker(selected_user_id)
        
        if success:
            await event.edit(
                f"✅ ADS STOPPED FOR USER\n\n"
                f"User: {username}\n"
                f"Status: 🔴 STOPPED"
            )
        else:
            await event.edit(f"❌ Failed: {message}")
        
        # Return to user management after delay
        await asyncio.sleep(3)
        await manage_user_callback(event)
        
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@bot.on(events.CallbackQuery(data=b"view_user_settings"))
async def view_user_settings_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get user info
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        selected_id_str = str(selected_user_id)
        username = data["usernames"].get(selected_id_str, "Unknown")
        limits = data["user_limits"].get(selected_id_str, {})
        current_sessions = count_user_accounts(selected_user_id)
        ads_running = is_user_worker_running(selected_user_id)
        
        msg = f"⚙️ USER SETTINGS\n\n"
        msg += f"Username: {username}\n"
        msg += f"User ID: {selected_user_id}\n"
        msg += f"Current Sessions: {current_sessions}\n"
        msg += f"Session Limit: {limits.get('max_sessions', 10)}\n"
        msg += f"Can Run Ads: {'✅ Yes' if limits.get('can_run_ads', True) else '❌ No'}\n"
        msg += f"Ads Status: {'🟢 RUNNING' if ads_running else '🔴 STOPPED'}\n"
        
        if current_sessions > 0:
            msg += f"\n📁 **Session Files:**\n"
            sessions = get_user_sessions(selected_user_id)
            for i, session in enumerate(sessions[:5], 1):
                api_id = session["api_id"] or "Unknown"
                if isinstance(api_id, int):
                    api_id = str(api_id)[:6]
                msg += f"{i}. {session['filename']} (API: {api_id})\n"
            
            if len(sessions) > 5:
                msg += f"... +{len(sessions)-5} more sessions\n"
        
        buttons = [[Button.inline("🔙 BACK", b"back_to_user_manage")]]
        await event.edit(msg, buttons=buttons)
        
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@bot.on(events.CallbackQuery(data=b"remove_user_confirm"))
async def remove_user_confirm_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    # Get user info
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        selected_id_str = str(selected_user_id)
        username = data["usernames"].get(selected_id_str, "Unknown")
        current_sessions = count_user_accounts(selected_user_id)
        
        buttons = [
            [Button.inline("✅ YES, REMOVE USER", b"remove_user_execute")],
            [Button.inline("❌ NO, CANCEL", b"back_to_user_manage")]
        ]
        
        await event.edit(
            f"⚠️ CONFIRM USER REMOVAL\n\n"
            f"Username: {username}\n"
            f"User ID: {selected_user_id}\n"
            f"Current Sessions: {current_sessions}\n\n"
            f"⚠️ **Warning:**\n"
            f"• User will lose access to bot\n"
            f"• All user sessions will be deleted\n"
            f"• Ads will be stopped if running\n"
            f"• This action cannot be undone\n\n"
            f"Are you sure?",
            buttons=buttons
        )
        
    except Exception as e:
        await event.edit(f"❌ Error: {str(e)}")

@bot.on(events.CallbackQuery(data=b"remove_user_execute"))
async def remove_user_execute_callback(event):
    admin_id = event.sender_id
    
    if admin_id not in user_selection:
        await event.answer("❌ No user selected!", alert=True)
        return
    
    selected_user_id = user_selection[admin_id]["selected_user"]
    
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        selected_id_str = str(selected_user_id)
        username = data["usernames"].get(selected_id_str, "Unknown")
        
        # Stop ads if running
        if is_user_worker_running(selected_user_id):
            stop_user_worker(selected_user_id)
            await asyncio.sleep(2)
        
        # Delete user sessions
        delete_all_user_sessions(selected_user_id)
        
        # Remove user from data
        if selected_user_id in data["users"]:
            data["users"].remove(selected_user_id)
        
        if selected_id_str in data["usernames"]:
            del data["usernames"][selected_id_str]
        
        if selected_id_str in data["user_folders"]:
            del data["user_folders"][selected_id_str]
        
        if selected_id_str in data["user_limits"]:
            del data["user_limits"][selected_id_str]
        
        # Save updated data
        with open("allowed_users.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # Delete user folder
        user_folder = f"users/user_{selected_user_id}_tdata"
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
        
        # Clear selection
        del user_selection[admin_id]
        
        await event.edit(
            f"✅ USER REMOVED\n\n"
            f"Username: {username}\n"
            f"User ID: {selected_user_id}\n"
            f"All data has been deleted."
        )
        
        # Return to user manager after delay
        await asyncio.sleep(3)
        await user_manager_callback(event)
        
    except Exception as e:
        await event.edit(f"❌ Error removing user: {str(e)}")

@bot.on(events.CallbackQuery(data=b"add_user"))
async def add_user_callback(event):
    admin_id = event.sender_id
    
    if not is_admin(admin_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    await event.delete()
    await event.respond(
        "➕ ADD NEW USER\n\n"
        "Send user ID and username in format:\n"
        "`USER_ID @username`\n\n"
        "Example:\n"
        "`123456789 @username`"
    )
    user_waiting[admin_id] = {"action": "add_user"}

@bot.on(events.CallbackQuery(data=b"view_all_users"))
async def view_all_users_callback(event):
    admin_id = event.sender_id
    
    if not is_admin(admin_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    users = get_all_users_with_info()
    
    if not users:
        await event.edit("❌ No users found.")
        return
    
    msg = f"📋 ALL USERS ({len(users)})\n\n"
    
    for i, user in enumerate(users, 1):
        ads_status = "🟢" if is_user_worker_running(user["id"]) else "🔴"
        msg += f"{i}. **{user['username']}**\n"
        msg += f"   ID: {user['id']}\n"
        msg += f"   Sessions: {user['current_sessions']}/{user['max_sessions']}\n"
        msg += f"   Ads: {'✅' if user['can_run_ads'] else '❌'} {ads_status}\n\n"
    
    buttons = [[Button.inline("🔙 BACK", b"user_manager")]]
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"back_main"))
async def back_main_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    # Clean up any dead workers first
    cleanup_workers()
    
    user_accounts = count_user_accounts(user_id)
    target = get_target()
    worker_running = is_user_worker_running(user_id)
    status = "🟢 RUNNING" if worker_running else "🔴 STOPPED"
    limits = get_user_limits(user_id)
    
    if is_admin(user_id):
        account_text = f"📱 Accounts: {user_accounts}\n"
    else:
        account_text = f"📱 Your Accounts: {user_accounts}/{limits['max_sessions']}\n"
    
    buttons = []
    
    if limits.get("can_run_ads", True):
        if worker_running:
            buttons.append([Button.inline("🛑 STOP MY ADS", b"stop_my_ads")])
        else:
            buttons.append([Button.inline("🚀 START MY ADS", b"start_my_ads")])
    
    buttons.append([
        Button.inline("🎯 SET TARGET", b"set_target"), 
        Button.inline("📊 STATUS", b"status")
    ])
    
    buttons.append([
        Button.inline("👤 MY ACCOUNTS", b"account_tools"), 
        Button.inline("⚙️ SETTINGS", b"settings")
    ])
    
    if is_admin(user_id):
        buttons.append([Button.inline("👥 USER MANAGER", b"user_manager")])
    
    await event.edit(
        f"🤖 **ORBIT MASTER**\n\n"
        f"👤 You: {'👑 ADMIN' if is_admin(user_id) else '👤 USER'}\n"
        f"{account_text}"
        f"🎯 Target: @{target if target else 'Not set'}\n"
        f"⚡ Ads Status: {status}\n"
        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}",
        buttons=buttons
    )

# ============================================
# MESSAGE HANDLERS
# ============================================
@bot.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        return
    
    text = event.text.strip()
    
    # Handle target setting
    if user_id in user_waiting and user_waiting[user_id].get("action") == "set_target":
        target = text.replace("@", "")
        save_target(target)
        await event.respond(f"✅ Target set to: @{target}")
        del user_waiting[user_id]
        return
    
    # Handle session count
    if user_id in session_waiting and session_waiting[user_id].get("step") == "waiting_count":
        try:
            count = int(text)
            limits = get_user_limits(user_id)
            current = count_user_accounts(user_id)
            remaining = limits["max_sessions"] - current
            
            if count < 1 or count > remaining:
                await event.respond(f"❌ Invalid number! Enter between 1 and {remaining}")
                return
            
            session_waiting[user_id] = {"step": "waiting_sessions", "count": count, "current": 1}
            await event.respond(f"📝 Now send API_ID for session 1/{count}:")
        except ValueError:
            await event.respond("❌ Please enter a valid number!")
        return
    
    # Handle session details
    if user_id in session_waiting and session_waiting[user_id].get("step") == "waiting_sessions":
        data = session_waiting[user_id]
        count = data["count"]
        current = data["current"]
        
        if "api_id" not in data:
            # First: API_ID
            data["api_id"] = text
            await event.respond(f"🔑 Now send API_HASH for session {current}/{count}:")
        
        elif "api_hash" not in data:
            # Second: API_HASH
            data["api_hash"] = text
            await event.respond(f"📱 Now send PHONE_NUMBER for session {current}/{count} (with country code):")
        
        elif "phone" not in data:
            # Third: PHONE_NUMBER
            data["phone"] = text
            
            # Now generate session
            await event.respond(f"🔄 Generating session {current}/{count}...")
            
            try:
                result = await session_generator.generate_session_parallel(
                    data["api_id"], 
                    data["api_hash"], 
                    data["phone"],
                    user_id
                )
                
                if result["status"] == "success":
                    session_data = {
                        "api_id": data["api_id"],
                        "api_hash": data["api_hash"],
                        "string_session": result["string_session"],
                        "generated_at": datetime.now().isoformat(),
                        "phone": data["phone"],
                        "proxy_used": True
                    }
                    
                    success, message = add_user_session(user_id, session_data)
                    
                    if success:
                        user_accounts = count_user_accounts(user_id)
                        await event.respond(
                            f"✅ Session {current}/{count} added!\n"
                            f"Phone: {data['phone']}\n"
                            f"Total sessions: {user_accounts}"
                        )
                    else:
                        await event.respond(f"❌ Failed to save: {message}")
                
                elif result["status"] == "needs_otp":
                    await event.respond(
                        f"🔢 OTP required for {data['phone']}\n"
                        f"Send OTP code received on phone:"
                    )
                    user_waiting[user_id] = {
                        "action": "otp",
                        "session_data": data,
                        "client": result["client"],
                        "sent_code": result["sent_code"],
                        "count": count,
                        "current": current
                    }
                    return
                
                else:
                    await event.respond(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                await event.respond(f"❌ Error: {str(e)}")
            
            # Move to next session or finish
            if current < count:
                data["current"] += 1
                data["api_id"] = None
                data["api_hash"] = None
                data["phone"] = None
                await event.respond(f"📝 Now send API_ID for session {data['current']}/{count}:")
            else:
                del session_waiting[user_id]
                await event.respond(f"✅ All {count} sessions processed!")
        return
    
    # Handle OTP input
    if user_id in user_waiting and user_waiting[user_id].get("action") == "otp":
        otp = text
        data = user_waiting[user_id]
        
        await event.respond("🔄 Verifying OTP...")
        
        try:
            result = await session_generator.process_otp(
                data["client"],
                data["session_data"]["phone"],
                data["sent_code"],
                otp
            )
            
            if result["status"] == "success":
                session_data = {
                    "api_id": data["session_data"]["api_id"],
                    "api_hash": data["session_data"]["api_hash"],
                    "string_session": result["string_session"],
                    "generated_at": datetime.now().isoformat(),
                    "phone": data["session_data"]["phone"],
                    "proxy_used": True
                }
                
                success, message = add_user_session(user_id, session_data)
                
                if success:
                    user_accounts = count_user_accounts(user_id)
                    await event.respond(
                        f"✅ Session {data['current']}/{data['count']} added!\n"
                        f"Phone: {data['session_data']['phone']}\n"
                        f"Total sessions: {user_accounts}"
                    )
                else:
                    await event.respond(f"❌ Failed to save: {message}")
            
            elif result["status"] == "needs_2fa":
                await event.respond(
                    f"🔐 2FA password required for {data['session_data']['phone']}\n"
                    f"Send 2FA password:"
                )
                user_waiting[user_id]["action"] = "2fa"
                return
            
            else:
                await event.respond(f"❌ OTP failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
        
        # Move to next session or finish
        if data["current"] < data["count"]:
            session_waiting[user_id] = {
                "step": "waiting_sessions",
                "count": data["count"],
                "current": data["current"] + 1
            }
            await event.respond(f"📝 Now send API_ID for session {session_waiting[user_id]['current']}/{data['count']}:")
        else:
            if user_id in user_waiting:
                del user_waiting[user_id]
            await event.respond(f"✅ All {data['count']} sessions processed!")
        return
    
    # Handle 2FA input
    if user_id in user_waiting and user_waiting[user_id].get("action") == "2fa":
        password = text
        data = user_waiting[user_id]
        
        await event.respond("🔄 Verifying 2FA password...")
        
        try:
            result = await session_generator.process_otp(
                data["client"],
                data["session_data"]["phone"],
                data["sent_code"],
                data.get("otp", ""),  # OTP was already entered
                password
            )
            
            if result["status"] == "success":
                session_data = {
                    "api_id": data["session_data"]["api_id"],
                    "api_hash": data["session_data"]["api_hash"],
                    "string_session": result["string_session"],
                    "generated_at": datetime.now().isoformat(),
                    "phone": data["session_data"]["phone"],
                    "proxy_used": True
                }
                
                success, message = add_user_session(user_id, session_data)
                
                if success:
                    user_accounts = count_user_accounts(user_id)
                    await event.respond(
                        f"✅ Session {data['current']}/{data['count']} added!\n"
                        f"Phone: {data['session_data']['phone']}\n"
                        f"Total sessions: {user_accounts}"
                    )
                else:
                    await event.respond(f"❌ Failed to save: {message}")
            else:
                await event.respond(f"❌ 2FA failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
        
        # Move to next session or finish
        if data["current"] < data["count"]:
            session_waiting[user_id] = {
                "step": "waiting_sessions",
                "count": data["count"],
                "current": data["current"] + 1
            }
            await event.respond(f"📝 Now send API_ID for session {session_waiting[user_id]['current']}/{data['count']}:")
        else:
            if user_id in user_waiting:
                del user_waiting[user_id]
            await event.respond(f"✅ All {data['count']} sessions processed!")
        return
    
    # Handle parallel session input
    if user_id in session_waiting and session_waiting[user_id].get("step") == "parallel_batch":
        try:
            lines = text.strip().split('\n')
            accounts = []
            current_account = {}
            
            for line in lines:
                line = line.strip()
                if line == '---':
                    if current_account:
                        if 'api_id' in current_account and 'api_hash' in current_account and 'phone' in current_account:
                            accounts.append(current_account)
                        current_account = {}
                    continue
                
                if 'api_id' not in current_account:
                    current_account['api_id'] = line
                elif 'api_hash' not in current_account:
                    current_account['api_hash'] = line
                elif 'phone' not in current_account:
                    current_account['phone'] = line
                    accounts.append(current_account)
                    current_account = {}
            
            # Add last account if exists
            if current_account and 'api_id' in current_account and 'api_hash' in current_account and 'phone' in current_account:
                accounts.append(current_account)
            
            if not accounts:
                await event.respond("❌ No valid accounts found in the format!")
                return
            
            # Check if exceeds limit
            limits = get_user_limits(user_id)
            current = count_user_accounts(user_id)
            remaining = limits["max_sessions"] - current
            
            if len(accounts) > remaining:
                await event.respond(f"❌ You can only add {remaining} more sessions!")
                return
            
            await event.respond(f"🔄 Processing {len(accounts)} accounts in parallel...")
            await process_parallel_sessions(user_id, accounts)
            
            del session_waiting[user_id]
            
        except Exception as e:
            await event.respond(f"❌ Error processing batch: {str(e)}")
        return
    
    # Handle parallel OTP input
    if user_id in user_waiting and user_waiting[user_id].get("action") == "parallel_otp":
        otp = text
        data = user_waiting[user_id]
        
        try:
            if user_id not in parallel_session_data:
                await event.respond("❌ Session data expired!")
                return
            
            parallel_data = parallel_session_data[user_id]
            otp_accounts = parallel_data.get("otp_required", [])
            
            if data["account_index"] >= len(otp_accounts):
                await event.respond("❌ Invalid account index!")
                return
            
            account = otp_accounts[data["account_index"]]
            
            await event.respond(f"🔄 Verifying OTP for {account['phone']}...")
            
            # Process OTP
            result = await session_generator.process_otp(
                account["client"],
                account["phone"],
                account["sent_code"],
                otp
            )
            
            if result["status"] == "success":
                # Update the account in results
                for i, res in enumerate(parallel_data["results"]):
                    if res.get("phone") == account["phone"]:
                        parallel_data["results"][i] = {
                            "status": "success",
                            "phone": account["phone"],
                            "api_id": account["api_id"],
                            "api_hash": account["api_hash"],
                            "string_session": result["string_session"],
                            "proxy_used": True
                        }
                        break
                
                # Remove from OTP required list
                otp_accounts.pop(data["account_index"])
                
                await event.respond(f"✅ OTP verified for {account['phone']}")
                
                # Update results display
                success_count = len([r for r in parallel_data["results"] if r.get("status") == "success"])
                failed_count = len([r for r in parallel_data["results"] if r.get("status") == "failed"])
                
                result_text = f"✅ **PARALLEL GENERATION UPDATED**\n\n"
                result_text += f"📊 **Results:**\n"
                result_text += f"• ✅ Successful: {success_count}\n"
                result_text += f"• ❌ Failed: {failed_count}\n"
                result_text += f"• 🔢 OTP Required: {len(otp_accounts)}\n\n"
                
                buttons = []
                if success_count > 0:
                    buttons.append([Button.inline("💾 ADD TO BOT", b"add_parallel_sessions")])
                
                if otp_accounts:
                    buttons.append([Button.inline("🔢 ENTER OTPs", b"enter_otps")])
                
                buttons.append([Button.inline("🔄 RETRY FAILED", b"retry_failed")])
                buttons.append([Button.inline("📋 VIEW ALL RESULTS", b"view_parallel_results")])
                
                # Find and update the progress message
                try:
                    await bot.edit_message(
                        user_id,
                        parallel_data["progress_msg_id"],
                        result_text,
                        buttons=buttons
                    )
                except:
                    pass
                
            elif result["status"] == "needs_2fa":
                await event.respond(
                    f"🔐 2FA password required for {account['phone']}\n"
                    f"Send 2FA password:"
                )
                user_waiting[user_id]["action"] = "parallel_2fa"
                return
            
            else:
                await event.respond(f"❌ OTP failed: {result.get('error', 'Unknown error')}")
            
            del user_waiting[user_id]
            
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
        return
    
    # Handle parallel 2FA input
    if user_id in user_waiting and user_waiting[user_id].get("action") == "parallel_2fa":
        password = text
        
        try:
            if user_id not in parallel_session_data:
                await event.respond("❌ Session data expired!")
                return
            
            # This would need more complex handling for 2FA in parallel mode
            # For simplicity, we'll just inform user to add this account separately
            await event.respond(
                "⚠️ 2FA detected in parallel mode\n\n"
                "For accounts with 2FA, please add them using the single session method."
            )
            
            del user_waiting[user_id]
            
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
        return
    
    # Handle admin adding user
    if user_id in user_waiting and user_waiting[user_id].get("action") == "add_user":
        try:
            parts = text.split()
            if len(parts) >= 2:
                user_id_to_add = int(parts[0])
                username = " ".join(parts[1:])
                
                if add_allowed_user(user_id_to_add, username):
                    await event.respond(f"✅ User added!\nID: {user_id_to_add}\nUsername: {username}")
                else:
                    await event.respond("❌ Failed to add user!")
            else:
                await event.respond("❌ Invalid format! Use: USER_ID @username")
        except ValueError:
            await event.respond("❌ Invalid user ID!")
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
        
        del user_waiting[user_id]
        return
    
    # Handle admin setting session limit
    if user_id in user_waiting and user_waiting[user_id].get("action") == "set_limit":
        try:
            limit = int(text)
            if 1 <= limit <= 100:
                target_user = user_waiting[user_id]["target_user"]
                update_user_limits(target_user, max_sessions=limit)
                
                # Get username
                try:
                    with open("allowed_users.json", "r") as f:
                        data = json.load(f)
                    username = data["usernames"].get(str(target_user), "Unknown")
                except:
                    username = "Unknown"
                
                await event.respond(
                    f"✅ Session limit updated!\n"
                    f"User: {username}\n"
                    f"New limit: {limit} sessions"
                )
            else:
                await event.respond("❌ Limit must be between 1 and 100!")
        except ValueError:
            await event.respond("❌ Please enter a valid number!")
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
        
        del user_waiting[user_id]
        return

# ============================================
# MAIN FUNCTION - FIXED
# ============================================
async def main():
    print("🤖 ORBIT MASTER BOT")
    print("==================")
    
    # Setup folders
    setup_folders()
    print("✅ Folders and files setup complete")
    
    # Start the bot with proper event loop handling
    print("🚀 Starting bot...")
    
    # Connect first
    await bot.connect()
    
    # Check authorization
    if not await bot.is_user_authorized():
        print("🔑 Logging in as bot...")
        await bot.start(bot_token=BOT_TOKEN)
    
    print(f"✅ Bot started as @{(await bot.get_me()).username}")
    
    # Keep running
    print("👂 Listening for commands...")
    await bot.run_until_disconnected()

# ============================================
# ENTRY POINT - FIXED FOR WINDOWS PYTHON 3.13
# ============================================
if __name__ == "__main__":
    # Use asyncio.run() with proper event loop policy for Windows
    try:
        if sys.platform == 'win32':
            # Windows-specific event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("👋 Bot shutdown complete")