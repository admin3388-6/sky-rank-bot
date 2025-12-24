import discord
import os
import io
import requests
from discord.ext import commands
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
from PIL import Image, ImageDraw, ImageOps, ImageFont

# --- الإعدادات الأساسية ---
token = os.getenv('DISCORD_TOKEN')
RULES_CHANNEL_ID = 1448638848513871872

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
CORS(app)

# إعدادات الترحيب (سيتم تحديث bg_url من الموقع)
welcome_config = {
    "channel_id": None,
    "bg_url": "https://i.ibb.co/m5m8Z8Y/welcome-bg.jpg"
}

@app.route('/get_channels')
def get_channels():
    channels = [{"id": str(c.id), "name": f"{c.guild.name} | #{c.name}"} 
                for g in bot.guilds for c in g.text_channels]
    return jsonify(channels)

@app.route('/save_welcome_settings', methods=['POST'])
def save_settings():
    global welcome_config
    data = request.json
    welcome_config.update(data)
    return jsonify({"status": "success"})

@bot.event
async def on_member_join(member):
    if not welcome_config["channel_id"]:
        return
    
    channel = bot.get_channel(int(welcome_config["channel_id"]))
    if not channel:
        return

    try:
        # 1. جلب خلفية الترحيب (الحجم 1408x736)
        bg_res = requests.get(welcome_config["bg_url"])
        bg = Image.open(io.BytesIO(bg_res.content)).convert("RGBA")
        
        # 2. جلب ومعالجة صورة البروفايل
        pfp_res = requests.get(member.display_avatar.url)
        pfp = Image.open(io.BytesIO(pfp_res.content)).convert("RGBA")
        
        # الحجم المحسوب بناءً على إحداثياتك
        pfp_size = (271, 271) 
        pfp = pfp.resize(pfp_size, Image.LANCZOS)
        
        # قناع دائري
        mask = Image.new('L', pfp_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + pfp_size, fill=255)
        
        pfp_circle = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
        pfp_circle.putalpha(mask)

        # 3. دمج الصور (الإحداثيات الدقيقة لمركزك 763, 332)
        paste_x = 627
        paste_y = 196
        bg.paste(pfp_circle, (paste_x, paste_y), pfp_circle)

        # 4. إرسال الصورة والرسالة النصية
        with io.BytesIO() as img_bin:
            bg.save(img_bin, 'PNG')
            img_bin.seek(0)
            
            member_count = member.guild.member_count
            msg_text = (f"مرحبا بك {member.mention}\n"
                        f"شكرا لانضمامك لـ **{member.guild.name}**\n"
                        f"عددنا الآن بعد دخولك: **{member_count}**\n"
                        f"لا تنسى قراءة القوانين في <#{RULES_CHANNEL_ID}>")
            
            await channel.send(msg_text, file=discord.File(fp=img_bin, filename='welcome.png'))
            
    except Exception as e:
        print(f"خطأ في نظام الترحيب: {e}")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    bot.run(token)
