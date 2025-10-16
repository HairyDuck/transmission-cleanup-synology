
# Transmission Cleanup Script

  

Automatically manages torrent files in Transmission by unselecting unwanted files (images, text files, executables, etc.) and removing torrents with no allowed files. Designed for **Synology NAS** with **Transmission 4.0.6**. Works standalone or as a companion script alongside **Sonarr** and **Radarr**.

  

## 🎯 What It Does

  

**Problem**: Torrents often contain unwanted files like images, text files, executables, and archives that waste bandwidth and storage.

  

**Solution**: This script automatically:

- ✅ **Unselects unwanted files** (stops them from downloading)

- ✅ **Keeps only your specified file types** (configurable)

- ✅ **Removes torrents** with no allowed files

- ✅ **Sends notifications** via webhook and/or Pushbullet

  

## 🏠 Synology NAS Ready

  

**Tested with**:

- Synology NAS (DSM 7.x)

- Transmission 4.0.6 (SynoCommunity)

- Python 3.x (built-in)

- Optional: Companion to Sonarr & Radarr

  

## 🚀 Quick Start

  

### 1. Download Script

```bash

# Clone or download the repository

git clone https://github.com/HairyDuck/transmission-cleanup-synology.git

cd transmission-cleanup-script

```

  

### 2. Configure

```bash

# Copy default configuration

cp default_config.json  config.json

  

# Edit with your settings

nano config.json

```

  

### 3. Test Run

```bash

# Test with dry run (safe)

python3 cleanup_transmission.py

```

  

### 4. Schedule on Synology

Set up a scheduled task in **Control Panel > Task Scheduler**:

-  **Task**: User-defined script

-  **Run command**:

```bash

/bin/bash -lc 'cd /path/to/your/scripts && /usr/bin/env python3 cleanup_transmission.py'

```

-  **Schedule**: Every 5-10 minutes

  

## ⚙️ Configuration

  

### Transmission Settings

```json

"transmission": {

"rpc_host": "localhost",

"rpc_port": "9091",

"rpc_user": "admin",

"rpc_pass": "admin"

}

```

  

### File Extensions (Fully Configurable)

```json

"file_extensions": {

"unwanted_exts": ["iso", "img", "jpg", "jpeg", "png", "gif", "bmp", "txt", "url", "nfo", "log", "exe"],

"allowed_exts": ["mkv", "mp4", "avi", "mov", "wmv", "flv", "webm", "m4v", "srt", "vtt", "ass", "ssa"]

}

```

  

**Customize for your needs**: Add/remove any file extensions you want to keep or block

  

### Webhook Notifications

```json

"webhook": {

"webhook_url": "https://your-webhook-url.com/",

"enabled": true,

"timeout": 10

}

```

  

### Pushbullet Notifications

```json

"pushbullet": {

"access_token": "your-pushbullet-access-token",

"enabled": true,

"device_iden": ""

}

```

  

**Note:** Leave `device_iden` empty to send to all devices, or specify a device ID for targeting.

  

### Notification Events

```json

"notifications": {

"send_on_unselect": true,

"send_on_remove": true,

"send_on_skip": false,

"send_on_keep": false

}

```

  

## 🔧 Synology NAS Setup

  

### 1. Install Transmission (SynoCommunity)

1. Add SynoCommunity repository to Package Center

2. Install **Transmission** package

3. Configure Transmission with RPC enabled

4. Note your RPC credentials (usually `admin:admin`)

  

### 2. Enable RPC Access

In Transmission settings:

-  **RPC enabled**: Yes

-  **RPC port**: 9091 (default)

-  **RPC username/password**: Set your credentials

-  **RPC whitelist**: Add your NAS IP or leave empty for localhost

  

### 3. Script Installation

```bash

# Create your scripts directory

mkdir -p  /path/to/your/scripts

cd /path/to/your/scripts

  

# Download and configure script

# (Follow Quick Start steps above)

```

  

### 4. Task Scheduler Setup

1.  **Control Panel** > **Task Scheduler**

2.  **Create** > **Triggered Task** > **User-defined script**

3.  **Task Settings**:

-  **Task name**: `Transmission Cleanup`

-  **User**: `your_user`

-  **Event**: `Time-based`

-  **Run command**:

```bash

/bin/bash -lc 'cd /path/to/your/scripts && /usr/bin/env python3 cleanup_transmission.py'

```

  

## 📱 Notifications

  

### Webhook Integration

The script sends structured JSON payloads to your webhook URL:

-  **Unselect**: `POST {webhook_url}/Unselect`

-  **Remove**: `POST {webhook_url}/Remove`

-  **Skip**: `POST {webhook_url}/Skip`

-  **Keep**: `POST {webhook_url}/Keep`

  

**Example payload:**

```json

{

"action": "Unselect",

"torrent_id": 37,

"torrent_name": "Movie.Name.2025.1080p",

"details": "Unselected 3 files",

"unselected_files": ["poster.jpg", "info.txt", "sample.iso"],

"timestamp": "2025-10-16T08:52:00",

"dry_run": false

}

```

  

### Pushbullet Integration

Get your access token from [Pushbullet Settings](https://www.pushbullet.com/#settings):

1.  **Account Settings** > **Access Tokens**

2.  **Create Access Token**

3.  **Copy token** to `config.json`

  

## 🔄 Sonarr/Radarr Companion (Optional)

  

**Perfect for**: Users with Sonarr/Radarr that often grab torrents with unwanted files

  

**How it works alongside Sonarr/Radarr**:

1.  **Sonarr/Radarr** → Downloads torrents to Transmission

2.  **Transmission** → Starts downloading

3.  **Cleanup Script** → Runs every 5-10 minutes, cleans up files

4.  **Sonarr/Radarr** → Imports clean files when download completes

  

**Benefits**: Cleaner downloads, bandwidth savings, automatic management

  

## 🎯 Use Cases

  

**Video/Media**: Keep `.mkv`, `.mp4`, `.srt` files, remove images and text files

**Software**: Keep `.exe`, `.msi`, `.dmg` files, remove documentation and samples

**Music**: Keep `.flac`, `.mp3`, `.m4a` files, remove images and text files

**Documents**: Keep `.pdf`, `.docx` files, remove images and archives

**Custom**: Configure any file types you want to keep or remove

  

## 📊 Logging

  

**Log Files**:

-  `cleanup_transmission.log` - Main activity log

-  `cleanup_processed.log` - Processed torrents tracking

  

**Features**: Automatic cleanup (30 days), configurable retention, detailed action tracking

  

## 🛡️ Safety Features

  

**Dry Run Mode**: Test safely before making changes

**Processed Tracking**: Skips already processed torrents

**Error Handling**: Graceful failures, detailed logging, safe defaults

  

## 🔧 Troubleshooting

  

**Common Issues**:

-  `transmission-remote: command not found` → Check Transmission installation path

-  `Command failed: Unknown option` → Verify RPC credentials and settings

-  `No torrents found` → Check Transmission is running and RPC enabled

  

**Debug**: Check log file for detailed output

  

## 📋 Requirements

  

**System**: Synology NAS (DSM 6.x/7.x), Python 3.x, Transmission 4.0.6

  

## 🤝 Contributing

  

**Issues**: Include logs and configuration details

**Pull Requests**: Test on Synology NAS, update documentation

  

---

  

**Happy torrenting! 🎬📺**
