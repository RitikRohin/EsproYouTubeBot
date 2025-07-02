import os
import json
import uuid
import threading
import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pyrogram import Client, filters

# ======= CONFIG ========
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 7666870729  # Replace with your Telegram ID
KEY_FILE = "apikeys.json"
ALLOWED_FILE = "allowed.json"
# ========================

# ====== FastAPI App =======
app = FastAPI()

class YouTubeData(BaseModel):
    title: str
    thumbnail: str
    duration: str
    direct_url: str

def extract_info(url: str, format_code: str):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "simulate": True,
        "forcejson": True,
        "format": format_code,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": f"{int(info['duration']//60)}:{int(info['duration']%60):02}",
            "direct_url": info.get("url"),
        }

def load_keys():
    if not os.path.exists(KEY_FILE):
        return {}
    with open(KEY_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(KEY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_allowed():
    if not os.path.exists(ALLOWED_FILE):
        return []
    with open(ALLOWED_FILE, "r") as f:
        return json.load(f)

def save_allowed(data):
    with open(ALLOWED_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.get("/")
def home():
    return {"message": "✅ YouTube API Server is Live!"}

@app.get("/video", response_model=YouTubeData)
def get_video(url: str = Query(...), apikey: str = Query(...)):
    keys = load_keys()
    if apikey not in keys.values():
        raise HTTPException(status_code=401, detail="❌ Invalid API Key")
    return extract_info(url, "18")

@app.get("/audio", response_model=YouTubeData)
def get_audio(url: str = Query(...), apikey: str = Query(...)):
    keys = load_keys()
    if apikey not in keys.values():
        raise HTTPException(status_code=401, detail="❌ Invalid API Key")
    return extract_info(url, "140")

# ========== Telegram Bot ==========
bot = Client("yt-api-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("👋 Welcome!\nUse /getkey to generate your API Key.")

@bot.on_message(filters.command("getkey"))
async def getkey(_, msg):
    user_id = str(msg.from_user.id)
    keys = load_keys()
    if user_id in keys:
        await msg.reply(f"🔑 Your API Key:\n`{keys[user_id]}`")
    else:
        key = uuid.uuid4().hex
        keys[user_id] = key
        save_keys(keys)
        await msg.reply(f"✅ API Key Generated:\n`{key}`")

@bot.on_message(filters.command("mykey"))
async def mykey(_, msg):
    user_id = str(msg.from_user.id)
    keys = load_keys()
    if user_id in keys:
        await msg.reply(f"🔑 Your API Key:\n`{keys[user_id]}`")
    else:
        await msg.reply("❌ You don’t have a key yet. Use /getkey")

@bot.on_message(filters.command("revoke"))
async def revoke(_, msg):
    user_id = str(msg.from_user.id)
    keys = load_keys()
    if user_id in keys:
        del keys[user_id]
        save_keys(keys)
        await msg.reply("🗑️ Your API Key has been revoked.")
    else:
        await msg.reply("❌ You don’t have a key to revoke.")

@bot.on_message(filters.command("allow") & filters.user(ADMIN_ID))
async def allow(_, msg):
    if len(msg.command) < 2:
        await msg.reply("Usage: /allow <user_id>")
        return
    uid = msg.command[1]
    allowed = load_allowed()
    if uid in allowed:
        await msg.reply("✅ Already allowed.")
    else:
        allowed.append(uid)
        save_allowed(allowed)
        await msg.reply(f"✅ User {uid} is now allowed.")

# ========== Run Both ==========

def start_bot():
    bot.run()

def start_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    start_api()
