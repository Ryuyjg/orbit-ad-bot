#!/usr/bin/env python3
import asyncio
import os
import json
import subprocess
import time
import shutil
from telethon import TelegramClient, events, Button
from datetime import datetime

# ============================================
# CONFIGURATION - LOAD FROM SECRET FILE
# ============================================
import secret
BOT_TOKEN = secret.BOT_TOKEN
MAIN_ADMIN_ID = secret.ADMIN_ID
MAIN_ADMIN_USERNAME = "@OrgJhonySins"

# ============================================
# INITIALIZE
# ============================================
bot = TelegramClient('orbit_master', 6, "eb06d4abfb49dc3eeb1aeb98ae0f581e")
worker_processes = {}
session_waiting = {}
user_waiting = {}
user_selection = {}
session_deletion = {}
user_session_pages = {}
delay_settings = {}

# ============================================
# SETUP FOLDERS
# ============================================
def setup_folders():
    folders = ["logs", "users", "admin_tdata"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    # Load or create config with delay settings
    if not os.path.exists("config.json"):
        default_config = {
            "target_user": "",
            "default_delays": {
                "between_groups_min": 60,
                "between_groups_max": 120,
                "cycle_delay_min": 900,
                "cycle_delay_max": 1500
            }
        }
        with open("config.json", "w") as f:
            json.dump(default_config, f, indent=2)
    
    if not os.path.exists("allowed_users.json"):
        initial_data = {
            "admins": [MAIN_ADMIN_ID],
            "users": [],
            "usernames": {},
            "user_folders": {},
            "user_limits": {},
            "user_delays": {}
        }
        with open("allowed_users.json", "w") as f:
            json.dump(initial_data, f, indent=2)
    else:
        try:
            with open("allowed_users.json", "r") as f:
                data = json.load(f)
            
            # Ensure all fields exist
            if "user_limits" not in data:
                data["user_limits"] = {}
            if "user_folders" not in data:
                data["user_folders"] = {}
            if "user_delays" not in data:
                data["user_delays"] = {}
            
            with open("allowed_users.json", "w") as f:
                json.dump(data, f, indent=2)
        except:
            pass

# ============================================
# DELAY SETTINGS MANAGEMENT
# ============================================
def get_default_delays():
    """Get default delay settings from config"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return config.get("default_delays", {
                "between_groups_min": 60,
                "between_groups_max": 120,
                "cycle_delay_min": 900,
                "cycle_delay_max": 1500
            })
    except:
        return {
            "between_groups_min": 60,
            "between_groups_max": 120,
            "cycle_delay_min": 900,
            "cycle_delay_max": 1500
        }

def get_user_delays(user_id):
    """Get delay settings for a specific user"""
    default = get_default_delays()
    
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        user_id_str = str(user_id)
        
        if user_id_str in data.get("user_delays", {}):
            user_delays = data["user_delays"][user_id_str]
            # Merge with defaults for missing values
            return {
                "between_groups_min": user_delays.get("between_groups_min", default["between_groups_min"]),
                "between_groups_max": user_delays.get("between_groups_max", default["between_groups_max"]),
                "cycle_delay_min": user_delays.get("cycle_delay_min", default["cycle_delay_min"]),
                "cycle_delay_max": user_delays.get("cycle_delay_max", default["cycle_delay_max"])
            }
    except:
        pass
    
    return default

def update_user_delays(user_id, delays):
    """Update delay settings for a user"""
    try:
        with open("allowed_users.json", "r") as f:
            data = json.load(f)
        
        user_id_str = str(user_id)
        
        if "user_delays" not in data:
            data["user_delays"] = {}
        
        data["user_delays"][user_id_str] = delays
        
        with open("allowed_users.json", "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error updating delays: {e}")
        return False

def update_default_delays(delays):
    """Update default delay settings"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        config["default_delays"] = delays
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

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
            # Set default delays for new user
            data["user_delays"][user_id_str] = get_default_delays()
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
            delays = data["user_delays"].get(user_id_str, get_default_delays())
            
            users.append({
                "id": user_id,
                "username": username,
                "max_sessions": limits.get("max_sessions", 10),
                "can_run_ads": limits.get("can_run_ads", True),
                "current_sessions": current_sessions,
                "delays": delays
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
# WORKER MANAGEMENT
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
        
        # Get user delay settings
        delays = get_user_delays(user_id)
        
        # Create config file for worker with delays
        worker_config = {
            "target_user": get_target(),
            "user_id": user_id,
            "delays": delays
        }
        
        with open(f"worker_config_{user_id}.json", "w") as f:
            json.dump(worker_config, f, indent=2)
        
        # Start worker with user_id as argument
        print(f"🚀 Starting worker for user {user_id} with delays: {delays}")
        process = subprocess.Popen(["python", "ad_worker.py", str(user_id)])
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
        
        # Clean up worker config
        config_file = f"worker_config_{user_id}.json"
        if os.path.exists(config_file):
            os.remove(config_file)
        
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
    
    if not is_allowed_user(user_id):
        await event.reply("❌ Unauthorized!")
        return
    
    user_accounts = count_user_accounts(user_id)
    target = get_target()
    worker_running = is_user_worker_running(user_id)
    status = "🟢 RUNNING" if worker_running else "🔴 STOPPED"
    limits = get_user_limits(user_id)
    delays = get_user_delays(user_id)
    
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
        f"⏱️ Delays: {delays['between_groups_min']}-{delays['between_groups_max']}s | {delays['cycle_delay_min']//60}-{delays['cycle_delay_max']//60}m\n"
        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}",
        buttons=buttons
    )

# ============================================
# DELAY SETTINGS MENU
# ============================================
@bot.on(events.CallbackQuery(data=b"settings"))
async def settings_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    limits = get_user_limits(user_id)
    delays = get_user_delays(user_id)
    
    msg = f"⚙️ YOUR SETTINGS\n\n"
    msg += f"Session Limit: {limits['max_sessions']}\n"
    msg += f"Current: {limits['current_sessions']}\n"
    msg += f"Can Run Ads: {'✅ Yes' if limits['can_run_ads'] else '❌ No'}\n\n"
    msg += f"⏱️ CURRENT DELAYS:\n"
    msg += f"Between Groups: {delays['between_groups_min']}-{delays['between_groups_max']} seconds\n"
    msg += f"Between Cycles: {delays['cycle_delay_min']//60}-{delays['cycle_delay_max']//60} minutes\n\n"
    
    buttons = [
        [Button.inline("⏱️ SET DELAYS", b"set_delays")],
        [Button.inline("🔄 RESET TO DEFAULT", b"reset_delays")],
        [Button.inline("🔙 BACK", b"back_main")]
    ]
    
    if is_admin(user_id):
        buttons.insert(0, [Button.inline("⚙️ SET DEFAULT DELAYS", b"set_default_delays")])
    
    await event.edit(msg, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"set_delays"))
async def set_delays_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    current_delays = get_user_delays(user_id)
    
    buttons = [
        [Button.inline(f"📤 Between Groups: {current_delays['between_groups_min']}-{current_delays['between_groups_max']}s", b"set_group_delay")],
        [Button.inline(f"🔄 Cycle Delay: {current_delays['cycle_delay_min']//60}-{current_delays['cycle_delay_max']//60}m", b"set_cycle_delay")],
        [Button.inline("✅ SAVE SETTINGS", b"save_delays")],
        [Button.inline("🔙 BACK", b"settings")]
    ]
    
    await event.edit(
        f"⏱️ SET DELAY TIMINGS\n\n"
        f"Current Settings:\n"
        f"• Between Groups: {current_delays['between_groups_min']}-{current_delays['between_groups_max']} seconds\n"
        f"• Between Cycles: {current_delays['cycle_delay_min']//60}-{current_delays['cycle_delay_max']//60} minutes\n\n"
        f"Click to change each setting:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(data=b"set_group_delay"))
async def set_group_delay_callback(event):
    user_id = event.sender_id
    
    await event.delete()
    await event.respond(
        "📤 SET BETWEEN GROUPS DELAY\n\n"
        "Send MIN and MAX seconds between groups:\n"
        "Format: `min max`\n\n"
        "Example: `60 120` for 1-2 minutes\n"
        "Recommended: 60-120 seconds"
    )
    user_waiting[user_id] = {"action": "set_group_delay"}

@bot.on(events.CallbackQuery(data=b"set_cycle_delay"))
async def set_cycle_delay_callback(event):
    user_id = event.sender_id
    
    await event.delete()
    await event.respond(
        "🔄 SET CYCLE DELAY\n\n"
        "Send MIN and MAX minutes between cycles:\n"
        "Format: `min max`\n\n"
        "Example: `15 25` for 15-25 minutes\n"
        "Recommended: 15-25 minutes"
    )
    user_waiting[user_id] = {"action": "set_cycle_delay"}

@bot.on(events.CallbackQuery(data=b"save_delays"))
async def save_delays_callback(event):
    user_id = event.sender_id
    
    # Get current delays (they should be in delay_settings dict)
    if user_id in delay_settings:
        delays = delay_settings[user_id]
        if update_user_delays(user_id, delays):
            await event.answer("✅ Delay settings saved!", alert=True)
            # Clear temporary storage
            if user_id in delay_settings:
                del delay_settings[user_id]
            await settings_callback(event)
        else:
            await event.answer("❌ Failed to save delays", alert=True)
    else:
        await event.answer("❌ No delay settings to save", alert=True)

@bot.on(events.CallbackQuery(data=b"reset_delays"))
async def reset_delays_callback(event):
    user_id = event.sender_id
    
    if not is_allowed_user(user_id):
        await event.answer("❌ Unauthorized!", alert=True)
        return
    
    default_delays = get_default_delays()
    
    if update_user_delays(user_id, default_delays):
        await event.answer("✅ Delays reset to default!", alert=True)
        await settings_callback(event)
    else:
        await event.answer("❌ Failed to reset delays", alert=True)

@bot.on(events.CallbackQuery(data=b"set_default_delays"))
async def set_default_delays_callback(event):
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    current_defaults = get_default_delays()
    
    buttons = [
        [Button.inline(f"📤 Default Groups: {current_defaults['between_groups_min']}-{current_defaults['between_groups_max']}s", b"set_default_group_delay")],
        [Button.inline(f"🔄 Default Cycle: {current_defaults['cycle_delay_min']//60}-{current_defaults['cycle_delay_max']//60}m", b"set_default_cycle_delay")],
        [Button.inline("✅ SAVE DEFAULTS", b"save_default_delays")],
        [Button.inline("🔙 BACK", b"settings")]
    ]
    
    await event.edit(
        f"⚙️ SET DEFAULT DELAYS\n\n"
        f"These will be used for new users:\n\n"
        f"Current Defaults:\n"
        f"• Between Groups: {current_defaults['between_groups_min']}-{current_defaults['between_groups_max']} seconds\n"
        f"• Between Cycles: {current_defaults['cycle_delay_min']//60}-{current_defaults['cycle_delay_max']//60} minutes\n\n"
        f"Click to change:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(data=b"set_default_group_delay"))
async def set_default_group_delay_callback(event):
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    await event.delete()
    await event.respond(
        "📤 SET DEFAULT BETWEEN GROUPS DELAY\n\n"
        "Send MIN and MAX seconds between groups:\n"
        "Format: `min max`\n\n"
        "Example: `60 120` for 1-2 minutes\n"
        "This will be default for all new users."
    )
    user_waiting[user_id] = {"action": "set_default_group_delay"}

@bot.on(events.CallbackQuery(data=b"set_default_cycle_delay"))
async def set_default_cycle_delay_callback(event):
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    await event.delete()
    await event.respond(
        "🔄 SET DEFAULT CYCLE DELAY\n\n"
        "Send MIN and MAX minutes between cycles:\n"
        "Format: `min max`\n\n"
        "Example: `15 25` for 15-25 minutes\n"
        "This will be default for all new users."
    )
    user_waiting[user_id] = {"action": "set_default_cycle_delay"}

@bot.on(events.CallbackQuery(data=b"save_default_delays"))
async def save_default_delays_callback(event):
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    
    # Get current delays from temporary storage
    if user_id in delay_settings and "default" in delay_settings[user_id]:
        delays = delay_settings[user_id]["default"]
        if update_default_delays(delays):
            await event.answer("✅ Default delays saved!", alert=True)
            # Clear temporary storage
            if user_id in delay_settings:
                del delay_settings[user_id]
            await set_default_delays_callback(event)
        else:
            await event.answer("❌ Failed to save defaults", alert=True)
    else:
        await event.answer("❌ No default delay settings to save", alert=True)

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
        buttons.append([Button.inline("➕ ADD SESSIONS", b"add_sessions")])
    else:
        buttons.append([Button.inline("❌ LIMIT REACHED", b"limit_reached")])
    
    if user_accounts > 0:
        buttons.append([Button.inline("🗑️ DELETE SESSIONS", b"delete_sessions")])
        buttons.append([Button.inline("🗑️ DELETE ALL SESSIONS", b"delete_all_sessions_confirm")])
    
    buttons.append([Button.inline(f"📁 MY SESSIONS ({user_accounts}/{limits['max_sessions']})", b"list_sessions")])
    buttons.append([Button.inline("🔙 BACK", b"back_main")])
    
    msg = f"👤 YOUR ACCOUNTS\n\n"
    msg += f"Sessions: {user_accounts}/{limits['max_sessions']}\n"
    msg += f"Ads Permission: {'✅ Yes' if limits['can_run_ads'] else '❌ No'}"
    
    await event.edit(msg, buttons=buttons)

# ... [Rest of the account management callbacks remain the same as before] ...

# ============================================
# MESSAGE HANDLER - UPDATED FOR DELAYS
# ============================================
@bot.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id
    text = event.text.strip()
    
    # Handle group delay setting
    if user_id in user_waiting and user_waiting[user_id].get("action") == "set_group_delay":
        try:
            parts = text.split()
            if len(parts) == 2:
                min_delay = int(parts[0])
                max_delay = int(parts[1])
                
                if 10 <= min_delay <= 300 and 10 <= max_delay <= 600 and min_delay <= max_delay:
                    # Store in temporary dict
                    if user_id not in delay_settings:
                        delay_settings[user_id] = get_user_delays(user_id)
                    
                    delay_settings[user_id]["between_groups_min"] = min_delay
                    delay_settings[user_id]["between_groups_max"] = max_delay
                    
                    del user_waiting[user_id]
                    await event.reply(
                        f"✅ Between Groups Delay Set\n\n"
                        f"Min: {min_delay} seconds\n"
                        f"Max: {max_delay} seconds\n\n"
                        f"Go to SETTINGS → SAVE SETTINGS to apply."
                    )
                else:
                    await event.reply("❌ Invalid values. Use: 10-300 seconds min, 10-600 seconds max, min ≤ max")
            else:
                await event.reply("❌ Format: `min max` (Example: `60 120`)")
        except:
            await event.reply("❌ Invalid numbers")
        
        if user_id in user_waiting:
            del user_waiting[user_id]
        return
    
    # Handle cycle delay setting
    if user_id in user_waiting and user_waiting[user_id].get("action") == "set_cycle_delay":
        try:
            parts = text.split()
            if len(parts) == 2:
                min_delay = int(parts[0])
                max_delay = int(parts[1])
                
                if 5 <= min_delay <= 60 and 5 <= max_delay <= 120 and min_delay <= max_delay:
                    # Store in temporary dict
                    if user_id not in delay_settings:
                        delay_settings[user_id] = get_user_delays(user_id)
                    
                    delay_settings[user_id]["cycle_delay_min"] = min_delay * 60  # Convert to seconds
                    delay_settings[user_id]["cycle_delay_max"] = max_delay * 60  # Convert to seconds
                    
                    del user_waiting[user_id]
                    await event.reply(
                        f"✅ Cycle Delay Set\n\n"
                        f"Min: {min_delay} minutes\n"
                        f"Max: {max_delay} minutes\n\n"
                        f"Go to SETTINGS → SAVE SETTINGS to apply."
                    )
                else:
                    await event.reply("❌ Invalid values. Use: 5-60 minutes min, 5-120 minutes max, min ≤ max")
            else:
                await event.reply("❌ Format: `min max` (Example: `15 25`)")
        except:
            await event.reply("❌ Invalid numbers")
        
        if user_id in user_waiting:
            del user_waiting[user_id]
        return
    
    # Handle default group delay setting (admin only)
    if user_id in user_waiting and user_waiting[user_id].get("action") == "set_default_group_delay":
        if is_admin(user_id):
            try:
                parts = text.split()
                if len(parts) == 2:
                    min_delay = int(parts[0])
                    max_delay = int(parts[1])
                    
                    if 10 <= min_delay <= 300 and 10 <= max_delay <= 600 and min_delay <= max_delay:
                        # Store in temporary dict
                        if user_id not in delay_settings:
                            delay_settings[user_id] = {}
                        
                        if "default" not in delay_settings[user_id]:
                            delay_settings[user_id]["default"] = get_default_delays()
                        
                        delay_settings[user_id]["default"]["between_groups_min"] = min_delay
                        delay_settings[user_id]["default"]["between_groups_max"] = max_delay
                        
                        del user_waiting[user_id]
                        await event.reply(
                            f"✅ Default Between Groups Delay Set\n\n"
                            f"Min: {min_delay} seconds\n"
                            f"Max: {max_delay} seconds\n\n"
                            f"Go to SETTINGS → SAVE DEFAULTS to apply."
                        )
                    else:
                        await event.reply("❌ Invalid values. Use: 10-300 seconds min, 10-600 seconds max, min ≤ max")
                else:
                    await event.reply("❌ Format: `min max` (Example: `60 120`)")
            except:
                await event.reply("❌ Invalid numbers")
        
        if user_id in user_waiting:
            del user_waiting[user_id]
        return
    
    # Handle default cycle delay setting (admin only)
    if user_id in user_waiting and user_waiting[user_id].get("action") == "set_default_cycle_delay":
        if is_admin(user_id):
            try:
                parts = text.split()
                if len(parts) == 2:
                    min_delay = int(parts[0])
                    max_delay = int(parts[1])
                    
                    if 5 <= min_delay <= 60 and 5 <= max_delay <= 120 and min_delay <= max_delay:
                        # Store in temporary dict
                        if user_id not in delay_settings:
                            delay_settings[user_id] = {}
                        
                        if "default" not in delay_settings[user_id]:
                            delay_settings[user_id]["default"] = get_default_delays()
                        
                        delay_settings[user_id]["default"]["cycle_delay_min"] = min_delay * 60
                        delay_settings[user_id]["default"]["cycle_delay_max"] = max_delay * 60
                        
                        del user_waiting[user_id]
                        await event.reply(
                            f"✅ Default Cycle Delay Set\n\n"
                            f"Min: {min_delay} minutes\n"
                            f"Max: {max_delay} minutes\n\n"
                            f"Go to SETTINGS → SAVE DEFAULTS to apply."
                        )
                    else:
                        await event.reply("❌ Invalid values. Use: 5-60 minutes min, 5-120 minutes max, min ≤ max")
                else:
                    await event.reply("❌ Format: `min max` (Example: `15 25`)")
            except:
                await event.reply("❌ Invalid numbers")
        
        if user_id in user_waiting:
            del user_waiting[user_id]
        return
    
    # ... [Rest of the message handler remains the same] ...

# ============================================
# UTILITY FUNCTIONS
# ============================================
def get_target():
    try:
        with open("config.json", "r") as f:
            return json.load(f).get("target_user", "")
    except:
        return ""

def set_target(username):
    try:
        if username.startswith("@"):
            username = username[1:]
        with open("config.json", "r") as f:
            config = json.load(f)
        config["target_user"] = username
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

# ============================================
# MAIN
# ============================================
async def main():
    print("=" * 50)
    print("🤖 ORBIT MASTER - DELAY CONTROL EDITION")
    print("=" * 50)
    print(f"Admin: {MAIN_ADMIN_USERNAME}")
    print("Features:")
    print("• Customizable delay settings")
    print("• Between groups: 60-120 seconds (configurable)")
    print("• Between cycles: 15-25 minutes (configurable)")
    print("• User-specific delay settings")
    print("• Admin can set default delays")
    print("=" * 50)
    
    setup_folders()
    
    # Clean stop files
    for file in os.listdir("."):
        if file.startswith("stop_worker") and file.endswith(".txt"):
            os.remove(file)
        if file.startswith("worker_config_") and file.endswith(".json"):
            os.remove(file)
    
    print("✅ Ready! Send /start in Telegram")
    print("=" * 50)
    
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped")
    except Exception as e:
        print(f"Error: {e}")
