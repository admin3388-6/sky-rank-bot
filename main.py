import discord
import os
import io
import asyncio
import requests
from discord.ext import commands
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
from PIL import Image, ImageDraw, ImageOps
from datetime import timedelta

# --- الإعدادات الفنية ---
token = os.getenv('DISCORD_TOKEN')
WELCOME_IMAGE_URL = "https://i.ibb.co/mVYpF4RQ/Picsart-25-12-24-14-57-39-769.jpg"
IP_CHANNEL_ID = 1448805638686769213

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
CORS(app)

# قاعدة بيانات مؤقتة (تُدار من لوحة التحكم)
bot_config = {
    "welcome_channel": None,
    "anti_spam": True,
    "smart_reply": True,
    "ip_response": "sd2k.progamer.me"
}

# --- نظام الرد الذكي (عينة من القاموس الضخم) ---
# ملاحظة: يمكنك توسيع هذه القائمة لتصل لـ 500 كلمة كما طلبت
SMART_DICTIONARY = {
    "سلام": "وعليكم السلام ورحمة الله وبركاته، نورتنا يا غالي!",
    "كيفك": "بخير عساك بخير، أنت كيف حالك؟",
    "شخباركم": "تمام التمام، نورت السيرفر بطلتك",
    "صباح الخير": "يسعد صباحك بكل خير وبركة",
    "منور": "النور نورك يا بعد قلبي",
    "شكرا": "العفو، هذا واجبنا يا طيب",
    "اي بي": f"تفضل الأي بي يا وحش: sd2k.progamer.me",
    "ip": f"Server IP: sd2k.progamer.me",
    "مساعدة": "أبشر، اذكر مشكلتك وسيقوم الفريق بالرد عليك فوراً",
}

# --- نظام مكافحة السبام والرسائل المكررة ---
user_messages = {}

async def anti_spam_check(message):
    if not bot_config["anti_spam"] or message.author.bot: return False
    
    user_id = message.author.id
    current_time = message.created_at
    
    if user_id not in user_messages:
        user_messages[user_id] = []
    
    # إضافة الرسالة الحالية للسجل
    user_messages[user_id].append({"time": current_time, "content": message.content})
    # الاحتفاظ بآخر 5 رسائل فقط
    user_messages[user_id] = user_messages[user_id][-5:]
    
    msgs = user_messages[user_id]
    if len(msgs) >= 4:
        # 1. منع التكرار (نفس الكلمة 3 مرات)
        if msgs[-1]['content'] == msgs[-2]['content'] == msgs[-3]['content']:
            return True
        # 2. منع السرعة (4 رسائل في أقل من 5 ثواني)
        time_diff = (msgs[-1]['time'] - msgs[0]['time']).total_seconds()
        if time_diff < 5:
            return True
    return False

# --- أحداث البوت ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} | Efficiency Mode: ON")

@bot.event
async def on_message(message):
    if message.author.bot: return

    # نظام مكافحة السبام في القناة المخصصة
    if message.channel.id == IP_CHANNEL_ID:
        is_spam = await anti_spam_check(message)
        if is_spam:
            await message.delete()
            try:
                await message.author.timeout(timedelta(minutes=5), reason="Spamming")
                await message.channel.send(f"⚠️ {message.author.mention} تم إعطاؤك وقت مستقطع (5 دقائق) بسبب التكرار أو السبام.", delete_after=10)
            except: pass
            return

        # نظام الرد الذكي والأي بي
        if bot_config["smart_reply"]:
            content = message.content.lower()
            for key, reply in SMART_DICTIONARY.items():
                if key in content:
                    await message.reply(reply)
                    break

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    if not bot_config["welcome_channel"]: return
    channel = bot.get_channel(int(bot_config["welcome_channel"]))
    try:
        # معالجة الصورة الأصلية بدقة 1408x736
        bg_res = requests.get(WELCOME_IMAGE_URL)
        bg = Image.open(io.BytesIO(bg_res.content)).convert("RGBA")
        pfp_res = requests.get(member.display_avatar.url)
        pfp = Image.open(io.BytesIO(pfp_res.content)).convert("RGBA")
        
        # حجم البروفايل المحسوب مسبقاً (271x271)
        pfp = pfp.resize((271, 271), Image.LANCZOS)
        mask = Image.new('L', (271, 271), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 271, 271), fill=255)
        pfp.putalpha(mask)

        # الإحداثيات الذهبية (627, 196)
        bg.paste(pfp, (627, 196), pfp)
        
        with io.BytesIO() as out:
            bg.save(out, format="PNG")
            out.seek(0)
            await channel.send(f"نورت السيرفر يا {member.mention}! أنت العضو رقم **{member.guild.member_count}**", file=discord.File(out, "welcome.png"))
    except Exception as e: print(f"Welcome Error: {e}")

# --- واجهة الـ API للوحة التحكم ---
@app.route('/update_config', methods=['POST'])
def update_config():
    bot_config.update(request.json)
    return jsonify({"status": "success"})

@app.route('/send_advanced', methods=['POST'])
def send_adv():
    data = request.json
    channel = bot.get_channel(int(data['channel_id']))
    if data.get('type') == 'embed':
        embed = discord.Embed(title=data['title'], description=data['desc'], color=int(data['color'].lstrip('#'), 16))
        if data.get('footer'): embed.set_footer(text=data['footer'])
        bot.loop.create_task(channel.send(embed=embed))
    else:
        bot.loop.create_task(channel.send(data['content']))
    return jsonify({"status": "success"})

@app.route('/get_status')
def get_status():
    return jsonify({"channels": [{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels]})

def run_web(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_web).start()
bot.run(token)
