import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
BOT_TOKEN = "8860437689:AAF--R4NwAje0xxdFLCcLX2lwGdu5Gp2YSk"
MONGO_URI = "mongodb+srv://Elevenyts:Elevenyts@cluster0.vuyc1u2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# --- MONGODB CONNECTION ---
try:
  client = MongoClient(MONGO_URI)
  db = client["nft_reward_project"]
  users_db = db["users"]
  sponsors_db = db["sponsor_links"]
  print("✅ MongoDB Successfully Connected!")
except Exception as e:
  print(f"❌ MongoDB Connection Error: {e}")

# --- TELEBOT & FLASK SETUP ---
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


@app.route("/")
def home():
  return "🚀 NFT Reward Bot is running 24/7 on Render!"


def run_web_server():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


def keep_alive():
  server_thread = threading.Thread(target=run_web_server)
  server_thread.daemon = True
  server_thread.start()


# --- BOT COMMANDS & HANDLERS ---
@bot.message_handler(commands=["start"])
def send_welcome(message):
  try:
    user_id = message.from_user.id
    current_time = datetime.utcnow()

    # Check 24-hour cooldown
    user_data = users_db.find_one({"user_id": user_id})

    if user_data:
      last_claim = user_data.get("last_claim_time")
      if last_claim and current_time - last_claim < timedelta(hours=24):
        time_left = timedelta(hours=24) - (current_time - last_claim)
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        bot.reply_to(
            message,
            f"⏳ **Cooldown Active!**\n\nAap apna agla free NFT **{hours} ghante {minutes} minute** baad claim kar sakenge. Tab tak naye links refresh nahi honge!",
            parse_mode="Markdown",
        )
        return

    # Fetch 3 active sponsor links from MongoDB
    active_links = list(sponsors_db.find({"status": "active"}).limit(3))
    markup = InlineKeyboardMarkup()

    if len(active_links) < 3:
      # Fallback links if database doesn't have 3 active links yet
      markup.add(
          InlineKeyboardButton("🔗 Visit Sponsor 1", url="https://google.com")
      )
      markup.add(
          InlineKeyboardButton("🔗 Visit Sponsor 2", url="https://google.com")
      )
      markup.add(
          InlineKeyboardButton("🔗 Visit Sponsor 3", url="https://google.com")
      )
    else:
      for link in active_links:
        markup.add(InlineKeyboardButton(f"🔗 {link['title']}", url=link["url"]))

    # Claim Button
    markup.add(
        InlineKeyboardButton("🎁 Claim Free NFT", callback_data="claim_nft")
    )

    bot.reply_to(
        message,
        "🔥 **Daily Free NFT Reward Program**\n\nNeeche diye gaye teeno sponsor links par click karke visit karein, aur uske baad **'Claim Free NFT'** button dabayein!",
        reply_markup=markup,
        parse_mode="Markdown",
    )
  except Exception as e:
    print(f"Error in start command: {e}")


@bot.callback_query_handler(func=lambda call: call.data == "claim_nft")
def handle_claim(call):
  try:
    user_id = call.from_user.id
    current_time = datetime.utcnow()

    # Verify cooldown again for security
    user_data = users_db.find_one({"user_id": user_id})
    if user_data:
      last_claim = user_data.get("last_claim_time")
      if last_claim and current_time - last_claim < timedelta(hours=24):
        bot.answer_callback_query(
            call.id,
            "❌ Aapka 24 ghante ka samay abhi poora nahi hua hai!",
            show_alert=True,
        )
        return

    # Update database with new claim timestamp and NFT count
    users_db.update_one(
        {"user_id": user_id},
        {"$set": {"last_claim_time": current_time}, "$inc": {"total_nfts": 1}},
        upsert=True,
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎉 **Badhai Ho!**\n\nAapka free NFT successfully claim ho gaya hai aur aapke account/safe mein save kar diya gaya hai.\n\n⏳ Ab agle 24 ghante baad naye links refresh honge!",
        parse_mode="Markdown",
    )
  except Exception as e:
    print(f"Error in claim handler: {e}")


# --- MAIN RUNNER ---
if __name__ == "__main__":
  print("🌐 Starting Flask Web Service...")
  keep_alive()

  print("🤖 Telegram Bot is running smoothly...")
  while True:
    try:
      bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
      print(f"⚠️ Polling Error: {e}")
      time.sleep(5)
