import telebot
import pyotp
import requests
import random
import time
import os
import threading
import re
from flask import Flask
from faker import Faker

# --- কনফিগারেশন ---
TOKEN = '8619212784:AAGNRWitsKF5EScwGnTvhUMAzatrGjj2Glo' 
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyPUCH-LmF-WOs6SyTYJ0zXtEtqA__YzSDJpLkMTjZmbHgnWpCYb8FT3iDcO97ar-pQ/exec"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
fake = Faker()

user_tasks = {}

@app.route('/')
def home():
    return "✅ Tanjim's UI Updated Bot is Running!"

# --- মেইল ও ওটিপি লজিক ---
def generate_tmail():
    username = fake.user_name() + str(random.randint(100, 999))
    domain = random.choice(["1secmail.com", "1secmail.net", "1secmail.org"])
    return username, domain

def fetch_live_otp(username, domain):
    try:
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={username}&domain={domain}"
        response = requests.get(url).json()
        if not response: return None
        msg_id = response[0]['id']
        read_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={username}&domain={domain}&id={msg_id}"
        msg_data = requests.get(read_url).json()
        body = msg_data.get('textBody', '')
        otp_match = re.findall(r'\b\d{4,6}\b', body)
        return otp_match[0] if otp_match else None
    except: return None

# --- কিবোর্ড মেনু (সব বাটন নিচে থাকবে) ---
def main_menu():
    # resize_keyboard=True দিলে বাটনগুলো মোবাইলের স্ক্রিন অনুযায়ী ছোট হয়ে নিচে সুন্দরভাবে থাকবে
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=False)
    
    btn1 = telebot.types.KeyboardButton('🧾 কাজ শুরু')
    btn2 = telebot.types.KeyboardButton('💰 প্রোফাইল')
    btn3 = telebot.types.KeyboardButton('👥 রেফার')
    btn4 = telebot.types.KeyboardButton('🏆 টপ ইউজার')
    btn5 = telebot.types.KeyboardButton('📞 সাপোর্ট')
    
    # বাটনগুলোকে সাজানো (প্রথম লাইনে বড় বাটন, পরের লাইনে ছোট বাটন)
    markup.add(btn1)
    markup.add(btn2, btn3, btn4)
    markup.add(btn5)
    return markup

# --- কমান্ড হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def welcome(message):
    welcome_text = (f"👋 স্বাগতম **{message.from_user.first_name}**!\n\n"
                    f"আপনার জন্য রিয়েল-টাইম ওটিপি সিস্টেম প্রস্তুত। "
                    f"নিচের বাটনগুলো ব্যবহার করে কাজ শুরু করুন।")
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- কাজ শুরু ---
@bot.message_handler(func=lambda message: message.text == "🧾 কাজ শুরু")
def provide_task(message):
    user, dom = generate_tmail()
    email = f"{user}@{dom}"
    password = fake.password(length=10)
    user_tasks[message.chat.id] = {"user": user, "dom": dom, "email": email, "pass": password}
    
    text = (f"╔════════════════════════╗\n"
            f"      📩 নতুন লাইভ টাস্ক 📩\n"
            f"╚════════════════════════╝\n"
            f"📧 মেইল: `{email}`\n"
            f"🔑 পাস: `{password}`\n\n"
            f"নির্দেশনা:\n১. এই মেইল দিয়ে সাইন-আপ করুন।\n২. ওটিপি সেন্ড হলে নিচের বাটনটি চাপুন।")
    
    # টাস্কের সাথে থাকা বাটনটি ইনলাইন থাকবে (মেসেজের সাথে)
    inline_markup = telebot.types.InlineKeyboardMarkup()
    inline_markup.add(telebot.types.InlineKeyboardButton("🔄 ওটিপি চেক করুন (Live)", callback_data="check_otp"))
    bot.send_message(message.chat.id, text, reply_markup=inline_markup, parse_mode="Markdown")

# --- ওটিপি বাটন লজিক ---
@bot.callback_query_handler(func=lambda call: call.data == "check_otp")
def otp_callback(call):
    data = user_tasks.get(call.message.chat.id)
    if not data:
        bot.answer_callback_query(call.id, "সেশন আউট!")
        return

    otp = fetch_live_otp(data['user'], data['dom'])
    if otp:
        bot.send_message(call.message.chat.id, f"✅ আপনার লাইভ ওটিপি: `{otp}`\n\nএখন আপনার **2FA Key** টি লিখে পাঠান।")
        bot.register_next_step_handler(call.message, get_2fa_live)
    else:
        bot.send_message(call.message.chat.id, "❌ ওটিপি আসেনি! ১০ সেকেন্ড পর আবার ট্রাই করুন।")

# --- ২এফএ লাইভ কোড ---
def get_2fa_live(message):
    key = message.text.replace(" ", "")
    try:
        totp = pyotp.TOTP(key)
        live_code = totp.now() 
        user_tasks[message.chat.id]['2fa_key'] = key
        
        inline_markup = telebot.types.InlineKeyboardMarkup()
        inline_markup.add(telebot.types.InlineKeyboardButton("🚀 গুগল শিটে জমা দিন", callback_data="final_submit"))
        
        bot.send_message(message.chat.id, f"🔐 আপনার লাইভ ২এফএ কোড: `{live_code}`\n\nসব ঠিক থাকলে সাবমিট করুন।", reply_markup=inline_markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ ভুল 2FA Key! সঠিক কী দিন।")

# --- মেনু হ্যান্ডলার (নিচের বাটনগুলোর কাজ) ---
@bot.message_handler(func=lambda message: message.text in ["💰 প্রোফাইল", "👥 রেফার", "🏆 টপ ইউজার", "📞 সাপোর্ট"])
def handle_menu(message):
    if message.text == "💰 প্রোফাইল":
        bot.send_message(message.chat.id, f"👤 ইউজার: {message.from_user.first_name}\n💰 ব্যালেন্স: ০.০০৳", reply_markup=main_menu())
    elif message.text == "📞 সাপোর্ট":
        bot.send_message(message.chat.id, "📞 সাপোর্ট অ্যাডমিন: @Tanjim_Admin", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "শীঘ্রই আপডেট আসছে...", reply_markup=main_menu())

# --- ডাটা সাবমিট ---
@bot.callback_query_handler(func=lambda call: call.data == "final_submit")
def final_submit(call):
    data = user_tasks.get(call.message.chat.id)
    if data:
        row = [str(time.ctime()), str(call.from_user.id), data['email'], data['pass'], data.get('2fa_key', 'N/A'), "Pending"]
        try:
            requests.post(WEB_APP_URL, json={"row": row}, timeout=15)
            bot.edit_message_text("🎉 সফলভাবে গুগল শিটে জমা হয়েছে!", call.message.chat.id, call.message.message_id)
            user_tasks.pop(call.message.chat.id, None)
        except:
            bot.send_message(call.message.chat.id, "❌ গুগল শিটে সেভ হয়নি।")

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    bot.infinity_polling()

