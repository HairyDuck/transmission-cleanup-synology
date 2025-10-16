#!/usr/bin/env python3
"""
Transmission Cleanup Script
Automatically unselects unwanted files and removes torrents with no allowed files.
"""

import subprocess
import re
import json
import sys
import requests
import os
from datetime import datetime, timedelta

# Load configuration from JSON file
def load_config():
    """Load configuration from config.json with fallback to default_config.json"""
    config_file = "config.json"
    default_config_file = "default_config.json"
    
    # Try to load user config first
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"[INFO] Loaded configuration from {config_file}")
            return config
        except Exception as e:
            print(f"[WARN] Failed to load config file {config_file}: {e}")
    
    # Fallback to default config
    if os.path.exists(default_config_file):
        try:
            with open(default_config_file, 'r') as f:
                config = json.load(f)
            print(f"[INFO] Using default configuration from {default_config_file}")
            return config
        except Exception as e:
            print(f"[WARN] Failed to load default config file: {e}")
    
    # If no config files exist, exit with error
    print(f"[ERROR] No configuration file found. Please create config.json or copy default_config.json to config.json")
    sys.exit(1)

# Load configuration
CONFIG = load_config()

# Extract configuration values
DRY_RUN = CONFIG["script"]["dry_run"]
RPC_HOST = CONFIG["transmission"]["rpc_host"]
RPC_PORT = CONFIG["transmission"]["rpc_port"]
RPC_USER = CONFIG["transmission"]["rpc_user"]
RPC_PASS = CONFIG["transmission"]["rpc_pass"]
TRANSMISSION_PATHS = CONFIG["transmission"]["transmission_paths"]
WEBHOOK_URL = CONFIG["webhook"]["webhook_url"]
PUSHBULLET_TOKEN = CONFIG["pushbullet"]["access_token"]
PUSHBULLET_DEVICE = CONFIG["pushbullet"]["device_iden"]
UNWANTED_EXTS = CONFIG["file_extensions"]["unwanted_exts"]
ALLOWED_EXTS = CONFIG["file_extensions"]["allowed_exts"]
PROCESSED_LOG = CONFIG["logging"]["processed_log_file"]
MAX_LOG_AGE_DAYS = CONFIG["logging"]["max_log_age_days"]

def cleanup_main_log():
    """Cleanup main log file to keep only last 30 days"""
    log_file = CONFIG["logging"]["main_log_file"]
    if not os.path.exists(log_file):
        return
    
    cutoff_date = datetime.now() - timedelta(days=MAX_LOG_AGE_DAYS)
    
    try:
        # Read all lines and filter out old ones
        valid_lines = []
        removed_count = 0
        
        with open(log_file, 'r') as f:
            for line in f:
                if len(line) >= 19:
                    try:
                        # Extract timestamp from line start
                        line_timestamp = datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
                        if line_timestamp >= cutoff_date:
                            valid_lines.append(line.rstrip('\n'))
                        else:
                            removed_count += 1
                    except ValueError:
                        # If timestamp parsing fails, keep the line
                        valid_lines.append(line.rstrip('\n'))
                else:
                    # If line is too short, keep it
                    valid_lines.append(line.rstrip('\n'))
        
        # Write back filtered lines
        if removed_count > 0:
            with open(log_file, 'w') as f:
                for line in valid_lines:
                    f.write(line + '\n')
            print(f"[CLEANUP] Removed {removed_count} old log entries from main log (older than {MAX_LOG_AGE_DAYS} days)")
    
    except Exception as e:
        print(f"[WARN] Failed to cleanup main log: {e}")

def cleanup_old_log_entries():
    """Remove old entries from processed log file"""
    if not os.path.exists(PROCESSED_LOG):
        return
    
    cutoff_date = datetime.now() - timedelta(days=MAX_LOG_AGE_DAYS)
    
    try:
        valid_lines = []
        removed_count = 0
        
        with open(PROCESSED_LOG, 'r') as f:
            for line in f:
                if len(line) >= 19:
                    try:
                        line_timestamp = datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
                        if line_timestamp >= cutoff_date:
                            valid_lines.append(line.rstrip('\n'))
                        else:
                            removed_count += 1
                    except ValueError:
                        valid_lines.append(line.rstrip('\n'))
                else:
                    valid_lines.append(line.rstrip('\n'))
        
        if removed_count > 0:
            with open(PROCESSED_LOG, 'w') as f:
                for line in valid_lines:
                    f.write(line + '\n')
            print(f"[CLEANUP] Removed {removed_count} old entries from processed log (older than {MAX_LOG_AGE_DAYS} days)")
    
    except Exception as e:
        print(f"[WARN] Failed to cleanup processed log: {e}")

def log(message):
    """Log message to main log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} {message}"
    
    try:
        with open(CONFIG["logging"]["main_log_file"], 'a') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"[WARN] Failed to write to log: {e}")
    
    # Also print to console
    print(log_entry)

def load_processed_torrents():
    """Load list of already processed torrents from log file"""
    processed = set()
    if os.path.exists(PROCESSED_LOG):
        try:
            with open(PROCESSED_LOG, 'r') as f:
                for line in f:
                    if 'TID=' in line:
                        # Extract TID from log line
                        match = re.search(r'TID=(\d+)', line)
                        if match:
                            processed.add(int(match.group(1)))
        except Exception as e:
            print(f"[WARN] Failed to load processed torrents: {e}")
    return processed

def mark_torrent_processed(tid):
    """Mark torrent as processed in log file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} [PROCESSED] TID={tid}"
    
    try:
        with open(PROCESSED_LOG, 'a') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"[WARN] Failed to mark torrent as processed: {e}")

def send_pushbullet_notification(action, tid, name, details="", unselected_files=None):
    """Send Pushbullet notification"""
    if not CONFIG["pushbullet"]["enabled"] or PUSHBULLET_TOKEN == "your-pushbullet-access-token":
        return  # Skip if Pushbullet disabled or token not configured
    
    # Create notification message
    title = f"Transmission Cleanup - {action}"
    
    if action == "Unselect":
        message = f"Unselected {len(unselected_files) if unselected_files else 0} files from '{name}'"
        if unselected_files and len(unselected_files) <= 3:
            message += f"\nFiles: {', '.join(unselected_files)}"
        elif unselected_files and len(unselected_files) > 3:
            message += f"\nFiles: {', '.join(unselected_files[:3])}... (+{len(unselected_files)-3} more)"
    elif action == "Remove":
        message = f"Removed torrent '{name}'\nReason: {details}"
    elif action == "Skip":
        message = f"Skipped torrent '{name}'\nReason: {details}"
    elif action == "Keep":
        message = f"Kept torrent '{name}'\nReason: {details}"
    else:
        message = f"Action: {action} on '{name}'\nDetails: {details}"
    
    if DRY_RUN:
        message = f"[DRY RUN] {message}"
    
    payload = {
        "type": "note",
        "title": title,
        "body": message
    }
    
    # Add device targeting if configured (skip if blank or default placeholder)
    if PUSHBULLET_DEVICE and PUSHBULLET_DEVICE != "your-device-identifier" and PUSHBULLET_DEVICE.strip():
        payload["device_iden"] = PUSHBULLET_DEVICE
    
    try:
        headers = {"Access-Token": PUSHBULLET_TOKEN}
        response = requests.post("https://api.pushbullet.com/v2/pushes", 
                               json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            log(f"[PUSHBULLET] Sent {action} notification for TID {tid}")
        else:
            log(f"[PUSHBULLET] Failed to send {action} notification: {response.status_code}")
    except Exception as e:
        log(f"[PUSHBULLET] Error sending {action} notification: {e}")

def send_webhook(action, tid, name, details="", unselected_files=None):
    """Send webhook notification with action indicator in URL"""
    if not CONFIG["webhook"]["enabled"] or WEBHOOK_URL == "https://your-webhook-url.com/Cleanup":
        return  # Skip if webhook disabled or URL not configured
    
    # Add action indicator to URL
    webhook_url = f"{WEBHOOK_URL}/{action}"
    
    payload = {
        "action": action,
        "torrent_id": tid,
        "torrent_name": name,
        "details": details,
        "timestamp": datetime.now().isoformat(),
        "dry_run": DRY_RUN
    }
    
    # Add unselected files as array for Unselect actions
    if unselected_files and action.startswith("Unselect"):
        payload["unselected_files"] = unselected_files
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=CONFIG["webhook"]["timeout"])
        if response.status_code == 200:
            log(f"[WEBHOOK] Sent {action} notification for TID {tid}")
        else:
            log(f"[WEBHOOK] Failed to send {action} notification: {response.status_code}")
    except Exception as e:
        log(f"[WEBHOOK] Error sending {action} notification: {e}")

def send_notification(action, tid, name, details="", unselected_files=None):
    """Send notifications based on configuration"""
    # Check if this action should trigger notifications
    should_notify = False
    
    if action == "Unselect" and CONFIG["notifications"]["send_on_unselect"]:
        should_notify = True
    elif action == "Remove" and CONFIG["notifications"]["send_on_remove"]:
        should_notify = True
    elif action == "Skip" and CONFIG["notifications"]["send_on_skip"]:
        should_notify = True
    elif action == "Keep" and CONFIG["notifications"]["send_on_keep"]:
        should_notify = True
    
    if not should_notify:
        return
    
    # Send webhook if configured
    send_webhook(action, tid, name, details, unselected_files)
    
    # Send Pushbullet if configured
    send_pushbullet_notification(action, tid, name, details, unselected_files)

def find_transmission_binary():
    """Find transmission-remote binary"""
    for path in TRANSMISSION_PATHS:
        if path == "transmission-remote":
            # Try to find in PATH
            try:
                result = subprocess.run(['which', 'transmission-remote'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
            except:
                continue
        else:
            # Try absolute path
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
    return None

def run_transmission_command(cmd_args):
    """Run transmission-remote command with proper authentication"""
    binary = find_transmission_binary()
    if not binary:
        raise Exception("transmission-remote binary not found")
    
    # Add authentication
    full_cmd = [binary, f"--auth={RPC_USER}:{RPC_PASS}"] + cmd_args
    
    # Set environment variable for host if not localhost:9091
    env = os.environ.copy()
    if RPC_HOST != "localhost" or RPC_PORT != "9091":
        env["TR_HOST"] = f"{RPC_HOST}:{RPC_PORT}"
    
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30, env=env)
        if result.returncode != 0:
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout
    except subprocess.TimeoutExpired:
        raise Exception("Command timed out")
    except Exception as e:
        raise Exception(f"Command error: {e}")

def get_torrent_list():
    """Get list of active torrents"""
    try:
        output = run_transmission_command(['-l'])
        torrents = []
        
        for line in output.split('\n'):
            if line.strip() and not line.startswith('ID'):
                parts = line.split()
                if len(parts) >= 10:
                    tid = int(parts[0])
                    # Extract name (everything after the last field)
                    name_parts = parts[9:]
                    name = ' '.join(name_parts)
                    torrents.append((tid, name))
        
        return torrents
    except Exception as e:
        log(f"[ERROR] Failed to get torrent list: {e}")
        return []

def get_torrent_files(tid):
    """Get files for a specific torrent"""
    try:
        output = run_transmission_command(['-t', str(tid), '-f'])
        files = []
        
        for line in output.split('\n'):
            line = line.strip()
            # Look for lines that start with a number (file entries) - same as old working script
            if re.match(r'^\s*\d+:', line):
                # Parse the line: "0: 0% Normal Yes 1.29 GB filename.ext"
                parts = line.split()
                if len(parts) >= 6:
                    index = parts[0].rstrip(':')
                    # Reconstruct filename from parts 6 onwards
                    filename = ' '.join(parts[6:])
                    
                    # Get file extension
                    ext = filename.split('.')[-1].lower() if '.' in filename else ''
                    
                    files.append({
                        'index': int(index),
                        'name': filename,
                        'extension': ext
                    })
        
        return files
    except Exception as e:
        log(f"[ERROR] Failed to get files for TID {tid}: {e}")
        return []

def unselect_files(tid, file_indices):
    """Unselect files by setting priority to 'off'"""
    if not file_indices:
        return True
    
    try:
        # Convert indices to comma-separated string
        indices_str = ','.join(map(str, file_indices))
        
        # Use -G flag to unselect files
        run_transmission_command(['-t', str(tid), '-G', indices_str])
        return True
    except Exception as e:
        log(f"[ERROR] Failed to unselect files for TID {tid}: {e}")
        return False

def remove_torrent(tid):
    """Remove torrent completely"""
    try:
        run_transmission_command(['-t', str(tid), '--remove-and-delete'])
        return True
    except Exception as e:
        log(f"[ERROR] Failed to remove TID {tid}: {e}")
        return False


def main():
    """Main cleanup logic"""
    log(f"Starting Transmission cleanup script (DRY_RUN={DRY_RUN})")
    
    # Cleanup old log entries
    cleanup_old_log_entries()
    cleanup_main_log()
    
    # Load processed torrents
    processed_torrents = load_processed_torrents()
    log(f"Loaded {len(processed_torrents)} previously processed torrents")
    
    # Get active torrents
    torrents = get_torrent_list()
    if not torrents:
        log("No torrents found")
        return
    
    log(f"Found {len(torrents)} active torrents")
    
    for tid, name in torrents:
        # Skip if already processed
        if tid in processed_torrents:
            continue
        
        log(f"Processing TID={tid} \"{name}\"")
        
        # Get files for this torrent
        files = get_torrent_files(tid)
        if not files:
            if CONFIG["script"]["skip_zero_file_torrents"]:
                log(f"[SKIP] TID={tid} has no files (likely just starting)")
                send_notification("Skip", tid, name, "No files found")
                continue
            else:
                log(f"[REMOVE] TID={tid} has no files, removing")
                if not DRY_RUN:
                    if remove_torrent(tid):
                        log(f"[SUCCESS] Removed TID={tid}")
                        send_notification("Remove", tid, name, "No files found")
                    else:
                        log(f"[ERROR] Failed to remove TID={tid}")
                else:
                    log(f"[DRY_RUN] Would remove TID={tid}")
                    send_notification("Remove", tid, name, "No files found")
                mark_torrent_processed(tid)
                continue
        
        # Analyze files
        unwanted_files = []
        allowed_files = []
        
        for file_info in files:
            filename = file_info['name']
            ext = file_info['extension']
            
            if ext in UNWANTED_EXTS:
                unwanted_files.append(file_info)
            elif ext in ALLOWED_EXTS:
                allowed_files.append(file_info)
        
        log(f"[ANALYSIS] TID={tid} - Unwanted: {len(unwanted_files)}, Allowed: {len(allowed_files)}")
        
        # Show which files are being processed
        if unwanted_files:
            unwanted_names = [f['name'] for f in unwanted_files]
            log(f"[UNWANTED] Files: {', '.join(unwanted_names[:5])}{'...' if len(unwanted_names) > 5 else ''}")
        
        if allowed_files:
            allowed_names = [f['name'] for f in allowed_files]
            log(f"[ALLOWED] Files: {', '.join(allowed_names[:5])}{'...' if len(allowed_names) > 5 else ''}")
        
        # Unselect unwanted files
        if unwanted_files:
            unwanted_indices = [f['index'] for f in unwanted_files]
            unwanted_names = [f['name'] for f in unwanted_files]
            
            log(f"[UNSELECT] TID={tid} unselecting {len(unwanted_files)} unwanted files")
            
            if not DRY_RUN:
                if unselect_files(tid, unwanted_indices):
                    log(f"[SUCCESS] Unselected {len(unwanted_files)} files in TID={tid}")
                    send_notification("Unselect", tid, name, f"Unselected {len(unwanted_files)} files", unwanted_names)
                else:
                    log(f"[ERROR] Failed to unselect files in TID={tid}")
            else:
                log(f"[DRY_RUN] Would unselect {len(unwanted_files)} files in TID={tid}")
                send_notification("Unselect", tid, name, f"Would unselect {len(unwanted_files)} files", unwanted_names)
        
        # Check if torrent should be removed (no allowed files)
        if not allowed_files:
            log(f"[REMOVE] TID={tid} has no allowed files, removing")
            if not DRY_RUN:
                if remove_torrent(tid):
                    log(f"[SUCCESS] Removed TID={tid}")
                    send_notification("Remove", tid, name, "No allowed files remaining")
                else:
                    log(f"[ERROR] Failed to remove TID={tid}")
            else:
                log(f"[DRY_RUN] Would remove TID={tid}")
                send_notification("Remove", tid, name, "No allowed files remaining")
        else:
            log(f"[KEEP] TID={tid} has {len(allowed_files)} allowed files, keeping")
            send_notification("Keep", tid, name, f"Kept {len(allowed_files)} allowed files")
        
        # Mark as processed
        mark_torrent_processed(tid)
    
    log("Transmission cleanup completed")

if __name__ == "__main__":
    main()