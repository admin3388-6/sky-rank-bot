import discord
import os
import io
import requests
from discord.ext import commands
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
from PIL import Image, ImageDraw, ImageOps
from datetime import timedelta

# --- الإعدادات ---
token = os.getenv('DISCORD_TOKEN')
IP_CHANNEL_ID = 1448805638686769213

intents = discord.Intents.all() # تفعيل جميع الحواس لضمان دقة الاستجابة
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
CORS(app) # حل مشكلة عدم الاستجابة (CORS)

# إعدادات ديناميكية
config = {
    "welcome_ch": None,
    "welcome_bg": "https://i.ibb.co/mVYpF4RQ/Picsart-25-12-24-14-57-39-769.jpg",
    "anti_spam": True,
    "smart_reply": True
}

# قاموس الرد الذكي الموسع (نموذج قابل للزيادة)
SMART_REPLIES = {
    "سلام": "وعليكم السلام يا هلا بك نورتنا!",
    "اي بي": "تفضل الأي بي يا وحش: `sd2k.progamer.me`",
    "ip": "Server IP: `sd2k.progamer.me`",
    "كيفكم": "بخير عساك بخير، نورت السيرفر",
    "وش السالفة": "سيرفرنا مخصص للألعاب والبرمجة، خذ لك لفة في القوانين"
}

# --- نظام الحماية ---
user_logs = {}

@bot.event
async def on_ready():
    print(f"✅ {bot.user} Online | High Performance Mode")

@bot.event
async def on_message(message):
    if message.author.bot: return

    # نظام مكافحة السبام المتطور
    if message.channel.id == IP_CHANNEL_ID and config["anti_spam"]:
        uid = message.author.id
        now = message.created_at
        
        if uid not in user_logs: user_logs[uid] = []
        user_logs[uid].append(message)
        
        # كشف التكرار والسرعة
        history = [m for m in user_logs[uid] if (now - m.created_at).total_seconds() < 10]
        if len(history) > 4 or (len(history) > 2 and history[-1].content == history[-2].content):
            await message.delete()
            try:
                await message.author.timeout(timedelta(minutes=5), reason="Spamming")
                await message.channel.send(f"⚠️ {message.author.mention} اهدأ قليلاً! تم إعطاؤك تايم آوت 5 دقائق.", delete_after=5)
            except: pass
            return

    # الرد الذكي
    if config["smart_reply"] and message.channel.id == IP_CHANNEL_ID:
        for key, val in SMART_REPLIES.items():
            if key in message.content.lower():
                await message.reply(val)
                break

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    if not config["welcome_ch"]: return
    channel = bot.get_channel(int(config["welcome_ch"]))
    try:
        res = requests.get(config["welcome_bg"])
        bg = Image.open(io.BytesIO(res.content)).convert("RGBA")
        pfp_res = requests.get(member.display_avatar.url)
        pfp = Image.open(io.BytesIO(pfp_res.content)).convert("RGBA").resize((271, 271), Image.LANCZOS)
        
        mask = Image.new('L', (271, 271), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 271, 271), fill=255)
        pfp.putalpha(mask)
        bg.paste(pfp, (627, 196), pfp) # نفس إحداثياتك الدقيقة
        
        with io.BytesIO() as out:
            bg.save(out, format="PNG")
            out.seek(0)
            await channel.send(f"حياك الله {member.mention} في سيرفرنا!", file=discord.File(out, "welcome.png"))
    except Exception as e: print(f"Error Welcome: {e}")

# --- API لوحة التحكم ---
@app.route('/api/status')
def get_status():
    guild = bot.guilds[0] if bot.guilds else None
    return jsonify({
        "members": guild.member_count if guild else 0,
        "channels": [{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels],
        "current_bg": config["welcome_bg"]
    })

@app.route('/api/update', methods=['POST'])
def update():
    config.update(request.json)
    return jsonify({"status": "ok"})

@app.route('/api/send', methods=['POST'])
def send():
    data = request.json
    channel = bot.get_channel(int(data['channel_id']))
    if data['type'] == 'embed':
        embed = discord.Embed(title=data['title'], description=data['desc'], color=int(data['color'].lstrip('#'), 16))
        bot.loop.create_task(channel.send(embed=embed))
    else:
        bot.loop.create_task(channel.send(data['content']))
    return jsonify({"status": "ok"})

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
bot.run(token)
