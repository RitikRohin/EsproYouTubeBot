import json
import uuid
import asyncio
import logging
import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pyrogram import Client, filters, idle
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, KEY_FILE, ALLOWED_FILE
import uvicorn

logging.basicConfig(level=logging.INFO)

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
    try:
        with open(KEY_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_keys(data):
    with open(KEY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_allowed():
    try:
        with open(ALLOWED_FILE) as f:
            return json.load(f)
    except:
        return []

def save_allowed(data):
    with open(ALLOWED_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.get("/")
def home():
    return {"message": "✅ API Server is Live!"}

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

bot = Client("yt-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("👋 Welcome! Use /getkey to get your API key.")

@bot.on_message(filters.command("getkey"))
async def getkey(_, msg):
    user_id = str(msg.from_user.id)
    keys = load_keys()
    if user_id not in keys:
        key = uuid.uuid4().hex
        keys[user_id] = key
        save_keys(keys)
    await msg.reply(f"🔑 Your API Key:\n`{keys[user_id]}`")

@bot.on_message(filters.command("mykey"))
async def mykey(_, msg):
    user_id = str(msg.from_user.id)
    keys = load_keys()
    if user_id in keys:
        await msg.reply(f"🔑 Your API Key:\n`{keys[user_id]}`")
    else:
        await msg.reply("❌ No key found. Use /getkey")

@bot.on_message(filters.command("revoke"))
async def revoke(_, msg):
    user_id = str(msg.from_user.id)
    keys = load_keys()
    if user_id in keys:
        del keys[user_id]
        save_keys(keys)
        await msg.reply("🗑️ API Key revoked.")
    else:
        await msg.reply("❌ No key to revoke.")

@bot.on_message(filters.command("allow") & filters.user(ADMIN_ID))
async def allow(_, msg):
    if len(msg.command) < 2:
        await msg.reply("Usage: /allow <user_id>")
        return
    uid = msg.command[1]
    allowed = load_allowed()
    if uid not in allowed:
        allowed.append(uid)
        save_allowed(allowed)
    await msg.reply(f"✅ Allowed user: {uid}")

async def main():
    await bot.start()
    print("✅ Bot is running.")
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
