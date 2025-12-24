import discord
import os
from discord.ext import commands
from flask import Flask, jsonify
from threading import Thread

# --- إعدادات البوت ---
token = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.members = True # لإظهار عدد الأعضاء مثلاً
bot = commands.Bot(command_prefix="!", intents=intents)

# --- إعدادات ويب API (لوحة التحكم) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت يعمل والواجهة متصلة!"

@app.route('/stats')
def get_stats():
    # هنا نرسل معلومات من البوت إلى صفحة الويب
    return jsonify({
        "server_count": len(bot.guilds),
        "user_count": sum(guild.member_count for guild in bot.guilds),
        "status": "Online"
    })

# وظيفة لتشغيل خادم Flask
def run_web():
    # Railway يتطلب التشغيل على Port 8080 غالباً أو المتغير المسمى PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- تشغيل الاثنين معاً ---
if __name__ == "__main__":
    # تشغيل خادم الويب في خلفية منفصلة
    t = Thread(target=run_web)
    t.start()
    
    # تشغيل البوت
    if token:
        bot.run(token)
