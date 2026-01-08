#!/usr/bin/env python3
import asyncio
import os
import json
import random
import sys
import time
from telethon import TelegramClient
from telethon.sessions import StringSession
from colorama import init, Fore

init(autoreset=True)

print("=" * 60)
print(Fore.CYAN + "🚀 ORBIT AD WORKER - RELIABLE VERSION")
print("=" * 60)

def get_user_id_from_args():
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
            print(Fore.YELLOW + f"👤 User Mode: Processing user {user_id}'s sessions")
            return user_id
        except:
            pass
    print(Fore.YELLOW + "👑 Admin Mode: Processing all sessions")
    return None

def load_config():
    try:
        with open("config.json", 'r') as f:
            config = json.load(f)
            target = config.get("target_user", "")
            if target:
                print(Fore.GREEN + f"🎯 Target: @{target}")
            return config
    except:
        return {"target_user": ""}

def load_user_sessions(user_id=None):
    accounts = []
    
    if user_id is None:
        # Load all sessions (admin + users)
        folders_to_check = ["admin_tdata"]
        if os.path.exists("users"):
            for folder in os.listdir("users"):
                if folder.startswith("user_") and folder.endswith("_tdata"):
                    folders_to_check.append(f"users/{folder}")
    else:
        # Load specific user sessions
        if user_id == 8055434763:  # Admin ID
            folders_to_check = ["admin_tdata"]
        else:
            user_folder = f"users/user_{user_id}_tdata"
            if os.path.exists(user_folder):
                folders_to_check = [user_folder]
            else:
                folders_to_check = []
                print(Fore.YELLOW + f"⚠️ No folder found for user {user_id}")
    
    for folder in folders_to_check:
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if f.startswith("session") and f.endswith(".json")]
            print(Fore.CYAN + f"📁 Loading from {folder}: {len(files)} sessions")
            
            for file in files:
                try:
                    filepath = os.path.join(folder, file)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        accounts.append({
                            "file": file,
                            "path": filepath,
                            "api_id": data.get("api_id"),
                            "api_hash": data.get("api_hash"),
                            "string_session": data.get("string_session"),
                            "folder": folder
                        })
                except Exception as e:
                    print(Fore.RED + f"❌ Failed {file}: {e}")
    
    print(Fore.GREEN + f"✅ Total sessions loaded: {len(accounts)}")
    return accounts

async def process_account(account_data, target_user, cycle_num, acc_num, total_accounts):
    try:
        session_name = account_data["file"].replace(".json", "")
        print(Fore.CYAN + f"\n[{cycle_num}.{acc_num}/{total_accounts}] {session_name}")
        print(Fore.WHITE + "─" * 40)
        
        client = TelegramClient(
            StringSession(account_data["string_session"]),
            account_data["api_id"],
            account_data["api_hash"]
        )
        
        print(Fore.YELLOW + "📡 Connecting...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print(Fore.RED + "❌ Not authorized")
            await client.disconnect()
            return False
        
        print(Fore.GREEN + "✅ Connected!")
        
        # Get target message
        try:
            print(Fore.YELLOW + f"📩 Getting message from: @{target_user}")
            entity = await client.get_input_entity(target_user)
            messages = await client.get_messages(entity, limit=1)
            
            if not messages:
                print(Fore.YELLOW + "⚠️ No messages")
                await client.disconnect()
                return True
            
            message = messages[0]
            print(Fore.GREEN + "✅ Got message")
        except Exception as e:
            print(Fore.RED + f"❌ Can't get messages: {e}")
            await client.disconnect()
            return True
        
        # Get groups
        groups = []
        try:
            print(Fore.YELLOW + "🔍 Searching groups...")
            async for dialog in client.iter_dialogs():
                if dialog.is_group:
                    groups.append(dialog.entity)
            
            if not groups:
                print(Fore.YELLOW + "⚠️ No groups")
                await client.disconnect()
                return True
                
            print(Fore.GREEN + f"✅ Found {len(groups)} groups")
        except Exception as e:
            print(Fore.RED + f"❌ Error: {e}")
            await client.disconnect()
            return True
        
        # Send to groups (limited to 30 groups per cycle)
        max_groups = 30
        groups_to_process = groups[:max_groups]
        groups_sent = 0
        
        for i, group in enumerate(groups_to_process, 1):
            try:
                group_title = getattr(group, 'title', 'Unknown')[:30]
                await client.forward_messages(group, message)
                groups_sent += 1
                print(Fore.GREEN + f"✅ [{i}] Sent to: {group_title}")
                
                # Wait between groups (1-2 minutes)
                if i < len(groups_to_process):
                    wait_time = random.randint(60, 120)
                    print(Fore.BLUE + f"⏳ Waiting {wait_time//60}m {wait_time%60}s...")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                error_msg = str(e)
                if any(x in error_msg for x in ["ChatWriteForbidden", "ChannelPrivate", "Forbidden"]):
                    print(Fore.YELLOW + f"⚠️ No access to group")
                elif "FloodWait" in error_msg:
                    print(Fore.RED + "⏳ Flood wait detected...")
                    await asyncio.sleep(300)
                else:
                    print(Fore.RED + f"❌ Error: {error_msg[:50]}")
                continue
        
        print(Fore.GREEN + f"\n🎯 Completed: {groups_sent}/{len(groups_to_process)} groups")
        await client.disconnect()
        return True
        
    except Exception as e:
        print(Fore.RED + f"❌ Critical error: {e}")
        return False

async def process_all_accounts_parallel(accounts, target_user, cycle_num):
    print(Fore.CYAN + f"\n🔄 CYCLE #{cycle_num}")
    print(Fore.CYAN + f"📱 Processing {len(accounts)} accounts")
    print(Fore.WHITE + "=" * 50)
    
    tasks = []
    for i, account in enumerate(accounts, 1):
        task = process_account(account, target_user, cycle_num, i, len(accounts))
        tasks.append(task)
    
    print(Fore.YELLOW + f"\n⚡ Starting parallel processing...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = 0
    failed = 0
    
    for result in results:
        if isinstance(result, Exception):
            failed += 1
        elif result:
            successful += 1
        else:
            failed += 1
    
    print(Fore.CYAN + f"\n📊 CYCLE #{cycle_num} RESULTS:")
    print(Fore.GREEN + f"✅ Successful: {successful}/{len(accounts)}")
    if failed > 0:
        print(Fore.RED + f"❌ Failed: {failed}/{len(accounts)}")
    
    return successful

def should_stop(user_id):
    """Check if stop signal received"""
    # Check user-specific stop file
    user_stop_file = f"stop_worker_{user_id}.txt"
    if os.path.exists(user_stop_file):
        print(Fore.RED + f"\n🛑 STOP SIGNAL RECEIVED for user {user_id}")
        os.remove(user_stop_file)
        return True
    
    # Check general stop file
    if os.path.exists("stop_worker.txt"):
        print(Fore.RED + f"\n🛑 GENERAL STOP SIGNAL RECEIVED")
        os.remove("stop_worker.txt")
        return True
    
    return False

async def main_worker():
    user_id = get_user_id_from_args()
    config = load_config()
    target_user = config.get("target_user", "")
    
    if not target_user:
        print(Fore.RED + "❌ ERROR: No target user set!")
        print(Fore.YELLOW + "👉 Set target in bot first")
        return
    
    # Load sessions for this user
    accounts = load_user_sessions(user_id)
    
    if not accounts:
        print(Fore.RED + "❌ ERROR: No accounts found!")
        if user_id:
            print(Fore.YELLOW + f"👉 User {user_id} has no sessions")
        else:
            print(Fore.YELLOW + "👉 Add sessions first")
        return
    
    print(Fore.CYAN + f"\n📊 SYSTEM READY")
    print(Fore.WHITE + f"• Target: @{target_user}")
    print(Fore.WHITE + f"• Accounts: {len(accounts)}")
    print(Fore.WHITE + f"• Mode: {'User Specific' if user_id else 'All Sessions'}")
    print(Fore.WHITE + "=" * 50)
    
    cycle = 1
    while True:
        # Check if we should stop
        if should_stop(user_id):
            break
        
        # Process accounts
        successful = await process_all_accounts_parallel(accounts, target_user, cycle)
        
        # Check if we should stop after cycle
        if should_stop(user_id):
            break
        
        print(Fore.CYAN + f"\n✅ CYCLE #{cycle} COMPLETE")
        
        # Wait 15-25 minutes between cycles
        wait_time = random.randint(900, 1500)  # 15-25 minutes in seconds
        print(Fore.YELLOW + f"⏳ Waiting {wait_time//60} minutes before next cycle...")
        
        # Check for stop signal during wait
        for _ in range(wait_time // 10):  # Check every 10 seconds
            if should_stop(user_id):
                return
            await asyncio.sleep(10)
        
        cycle += 1
        print(Fore.WHITE + "\n" + "=" * 50)

if __name__ == "__main__":
    try:
        asyncio.run(main_worker())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n🛑 Worker stopped by user")
    except Exception as e:
        print(Fore.RED + f"❌ Worker crashed: {e}")
    finally:
        print(Fore.CYAN + "\n👋 Worker shutdown complete")
