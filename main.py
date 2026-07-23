import os
import threading
import time
import random
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
BOT_TOKEN = "8860437689:AAF--R4NwAje0xxdFLCcLX2lwGdu5Gp2YSk"
API_ID = 29500000  # Apna Telegram API_ID yahan dalein (my.telegram.org se milega)
API_HASH = "aapka_telegram_api_hash"  # Apna API_HASH yahan dalein
MONGO_URI = "mongodb+srv://Elevenyts:Elevenyts@cluster0.vuyc1u2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# --- MONGODB CONNECTION ---
try:
    client = MongoClient(MONGO_URI)
    db = client["nft_reward_project"]
    users_db = db["users"]
    sponsors_db = db["sponsor_links"]
    safes_db = db["user_safes"]
    sessions_db = db["user_sessions"]
    print("✅ MongoDB Successfully Connected!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# --- FLASK SETUP FOR RENDER 24/7 ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "🚀 Telegram Login NFT Bot is running 24/7 on Render!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host="0.0.0.0", port=port)

def keep_alive():
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

# --- PYROGRAM BOT SETUP ---
bot = Client(
    "nft_bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@bot.on_message(filters.command("start"))
def start_handler(client, message):
    user_id = message.from_user.id
    
    # Check if user session already exists in DB
    session_data = sessions_db.find_one({"user_id": user_id})
    
    if not session_data:
        # Agar user logged in nahi hai, toh login command ya message bhejo
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔐 Ek Baar Login Karein", callback_data="start_login")
        ]])
        message.reply(
            "👋 **Swagat hai!**\n\nFree NFT aur Gifts claim karne ke liye aapko apna Telegram account **ek hi baar** login karna padega taaki gift seedha aapke account mein transfer ho sake.",
            reply_markup=keyboard
        )
        return

    # Agar login hai, toh tasks aur 24-hour cooldown check karo
    current_time = datetime.utcnow()
    user_data = users_db.find_one({"user_id": user_id})

    if user_data:
        last_claim = user_data.get("last_claim_time")
        if last_claim and current_time - last_claim < timedelta(hours=24):
            time_left = timedelta(hours=24) - (current_time - last_claim)
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            
            message.reply(
                f"⏳ **Cooldown Active!**\n\nAap apna agla gift **{hours} ghante {minutes} minute** baad claim kar sakenge."
            )
            return

    # Fetch 3 active sponsor links
    active_links = list(sponsors_db.find({"status": "active"}).limit(3))
    markup_list = []

    if len(active_links) < 3:
        markup_list.append([InlineKeyboardButton("🔗 Visit Sponsor 1", url="https://google.com")])
        markup_list.append([InlineKeyboardButton("🔗 Visit Sponsor 2", url="https://google.com")])
        markup_list.append([InlineKeyboardButton("🔗 Visit Sponsor 3", url="https://google.com")])
    else:
        for link in active_links:
            markup_list.append([InlineKeyboardButton(f"🔗 {link['title']}", url=link['url'])])

    markup_list.append([InlineKeyboardButton("🎁 Claim Free Gift / NFT", callback_data="claim_gift")])
    
    message.reply(
        "🔥 **Daily Free Gift System**\n\nNeeche diye gaye links par visit karein aur 'Claim Free Gift' par click karein!",
        reply_markup=InlineKeyboardMarkup(markup_list)
    )

@bot.on_callback_query(filters.regex("start_login"))
def login_prompt(client, callback_query):
    callback_query.message.reply(
        "📲 **Login Process:**\n\n"
        "Kripya apna phone number international format mein bhejein (Jaise: `+919876543210`).\n"
        "*(Note: Yeh ek secure connection hai, aapka data safe rahega.)*"
    )
    # Yahan aap FSM state maintain karke phone number aur OTP handle kar sakte hain

@bot.on_callback_query(filters.regex("claim_gift"))
def claim_gift_handler(client, callback_query):
    user_id = callback_query.from_user.id
    current_time = datetime.utcnow()

    # Cooldown verification
    user_data = users_db.find_one({"user_id": user_id})
    if user_data:
        last_claim = user_data.get("last_claim_time")
        if last_claim and current_time - last_claim < timedelta(hours=24):
            callback_query.answer("❌ 24 ghante ka cooldown abhi baaki hai!", show_alert=True)
            return

    # Generate Gift Item
    gift_number = random.randint(10000, 99999)
    gift_name = f"Candy Cane #{gift_number}"
    
    # Save to Database Safe
    users_db.update_one(
        {"user_id": user_id},
        {"$set": {"last_claim_time": current_time}, "$inc": {"total_gifts": 1}},
        upsert=True
    )
    
    safes_db.update_one(
        {"user_id": user_id},
        {"$push": {"safe_inventory": {"name": gift_name, "date": current_time}}},
        upsert=True
    )

    callback_query.message.edit_text(
        f"🎉 **Badhai Ho!**\n\nAapka naya gift **{gift_name}** successfully aapke account ke **Safe** mein transfer kar diya gaya hai!\n\n⏳ Ab agle 24 ghante baad naye links refresh honge."
    )

# --- MAIN RUNNER ---
if __name__ == "__main__":
    print("🌐 Starting Flask Web Service for Render...")
    keep_alive()
    
    print("🤖 Pyrogram Bot is starting...")
    bot.run()
