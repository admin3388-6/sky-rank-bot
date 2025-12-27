import discord
from discord.ext import commands
from discord import app_commands
import os, json, random, asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread

# --- الإعدادات ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"

def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except: return {"users": {}, "config": {}}

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# دالة جلب الصور (تأكد من صحة الروابط)
def get_rank_image(level):
    ranks = {
        (0, 5): "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png",
        (6, 15): "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png",
        (16, 50): "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"
    }
    for (low, high), url in ranks.items():
        if low <= level <= high: return url
    return ranks[(0, 5)]

class SkyBot(commands.Bot):
    def __init__(self):
        # تفعيل كافة الصلاحيات لضمان عدم حدوث Unknown Integration
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # الخطوة الأهم: مسح الأوامر القديمة من ذاكرة ديسكورد ثم إعادة تسجيلها
        print("🔄 جاري تحديث التكامل (Integration)...")
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        print("✅ تم تحديث الهوية بنجاح!")

bot = SkyBot()

@bot.tree.command(name="rank", description="عرض بطاقتك وتفاعلك")
async def rank(interaction: discord.Interaction):
    # استخدام defer لتجنب خطأ التأخير في الرد
    await interaction.response.defer()
    
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0})
    
    embed = discord.Embed(
        title=f"📊 بطاقة تفاعل {interaction.user.display_name}",
        description=f"المستوى: **{u['level']}**\nالخبرة: **{u['xp']}**",
        color=0x00d2ff
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=get_rank_image(u["level"]))
    
    # الرد النهائي بعد المعالجة
    await interaction.followup.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    if uid not in db["users"]:
        db["users"][uid] = {"xp": 0, "level": 0}
    
    db["users"][uid]["xp"] += random.randint(5, 15)
    # نظام ترقية بسيط
    if db["users"][uid]["xp"] > (db["users"][uid]["level"] + 1) * 100:
        db["users"][uid]["level"] += 1
        
    save_db(db)
    await bot.process_commands(message)

# --- واجهة الموقع (API) ---
app = Flask(__name__)
CORS(app)

@app.route('/api/full_stats')
def full_stats():
    top_users = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    return jsonify({
        "members": len(db["users"]),
        "top_users": top_users
    })

def run_api():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_api).start()
    bot.run(TOKEN)
