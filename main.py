import discord
from discord.ext import commands
from discord import app_commands
import os, io, requests, asyncio, math, json
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# --- الإعدادات الأساسية ---
TOKEN = os.getenv('DISCORD_TOKEN')
WELCOME_IMG = "https://i.ibb.co/mVYpF4RQ/Picsart-25-12-24-14-57-39-769.jpg"
DATA_FILE = "users_data.json"

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.user_data = self.load_data()

    def load_data(self):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {}

    def save_data(self):
        with open(DATA_FILE, "w") as f: json.dump(self.user_data, f)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user.name}")

bot = MyBot()

# --- نظام الـ XP المتقدم ---
async def add_xp(user_id, amount):
    uid = str(user_id)
    if uid not in bot.user_data:
        bot.user_data[uid] = {"xp": 0, "level": 1, "messages": 0}
    
    bot.user_data[uid]["xp"] += amount
    bot.user_data[uid]["messages"] += 1
    
    # معادلة المستوى: XP = 100 * (level ^ 1.5)
    current_xp = bot.user_data[uid]["xp"]
    current_lvl = bot.user_data[uid]["level"]
    next_lvl_xp = 100 * (current_lvl ** 1.5)
    
    if current_xp >= next_lvl_xp and current_lvl < 50:
        bot.user_data[uid]["level"] += 1
        return True
    return False

# --- قاموس الردود الذكية (هيكل لـ 500 كلمة) ---
# يمكنك ملء هذا القاموس بكل اللهجات
SMART_REPLIES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته يا هلا!",
    "كيف حالك": "بخير عساك بخير يا وحش، نورتنا",
    "منور": "النور نورك ونور الموجودين يا غالي",
    "ip": "تفضل الأي بي يا بطل: `sd2k.progamer.me`",
    "اي بي": "تفضل الأي بي يا بطل: `sd2k.progamer.me`",
    "شكرا": "العفو، ماسوينا إلا الواجب!",
    "وين الادارة": "الإدارة موجودة لخدمتك، اترك رسالتك وسيردون عليك",
    # أضف هنا الـ 500 كلمة المتبقية بنفس التنسيق...
}

# --- أحداث البوت ---
@bot.event
async def on_member_join(member):
    # 1. ترحيب الصورة (في الروم)
    # [كود معالجة الصورة السابق وضعه هنا]
    
    # 2. ترحيب الخاص (DM)
    embed = discord.Embed(
        title=f"أهلاً بك {member.name} في Sky Data! 🎉",
        description="شكراً لانضمامك إلينا يا وحش! استمتع بوقتك.\nإذا واجهت أي مشكلة، لا تتردد في فتح تذكرة مساعدة.",
        color=0x00d2ff
    )
    embed.set_footer(text="نتمنى لك قضاء وقت ممتع")
    try: await member.send(embed=embed)
    except: pass

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # إضافة XP (15-25 نقطة عشوائية)
    leveled_up = await add_xp(message.author.id, 20)
    if leveled_up:
        await message.channel.send(f"🎉 كفو {message.author.mention}! ارتقيت للمستوى **{bot.user_data[str(message.author.id)]['level']}**")
    
    # الرد الذكي
    for key, reply in SMART_REPLIES.items():
        if key in message.content:
            await message.reply(reply)
            break
            
    bot.save_data()
    await bot.process_commands(message)

# --- أوامر Slash ---
@bot.tree.command(name="rank", description="عرض مستواك وترتيبك")
async def rank(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    data = bot.user_data.get(uid, {"xp": 0, "level": 1})
    embed = discord.Embed(title=f"رتبة {interaction.user.name}", color=0x00d2ff)
    embed.add_field(name="المستوى", value=data["level"])
    embed.add_field(name="النقاط (XP)", value=f"{data['xp']}/{int(100 * (data['level']**1.5))}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="عرض قائمة الأوامر")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="قائمة أوامر Sky Data", color=0x00d2ff)
    embed.add_field(name="/rank", value="لعرض مستواك وتفاعلك", inline=False)
    embed.add_field(name="/help", value="لعرض هذه القائمة", inline=False)
    await interaction.response.send_message(embed=embed)

# --- واجهة الـ API للوحة التحكم ---
app = Flask(__name__)
CORS(app)

@app.route('/api/stats')
def get_stats():
    guild = bot.guilds[0] if bot.guilds else None
    online = len([m for m in guild.members if m.status != discord.Status.offline]) if guild else 0
    return jsonify({
        "server_name": guild.name if guild else "N/A",
        "members": guild.member_count if guild else 0,
        "online": online,
        "servers_count": len(bot.guilds),
        "channels": [{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels]
    })

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    channel = bot.get_channel(int(data['channel_id']))
    if data['type'] == 'msg':
        bot.loop.create_task(channel.send(data['content']))
    return jsonify({"status": "success"})

def run_flask(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_flask).start()
bot.run(TOKEN)
