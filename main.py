import discord
from discord.ext import commands
from discord import app_commands
import os, json, random, asyncio
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread

# --- الإعدادات وقاعدة البيانات ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"

def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except: return {"users": {}}

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- دالة جلب صورة الرتبة بناءً على المستوى (دقيقة جداً) ---
def get_rank_image(level):
    if 0 <= level <= 2: return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    if 3 <= level <= 5: return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    if 6 <= level <= 8: return "https://i.ibb.co/fztgZ8hG/Picsart-25-12-27-22-57-38-916.png"
    if 9 <= level <= 10: return "https://i.ibb.co/rfy0BDn6/Picsart-25-12-27-22-58-03-096.png"
    if 11 <= level <= 13: return "https://i.ibb.co/Wvfqm8v5/Picsart-25-12-27-22-58-10-424.png"
    if 14 <= level <= 15: return "https://i.ibb.co/0Rrpz67D/Picsart-25-12-27-22-58-15-557.png"
    if 16 <= level <= 20: return "https://i.ibb.co/hx51cSSB/Picsart-25-12-27-22-58-24-170.png"
    if 21 <= level <= 25: return "https://i.ibb.co/tpsztsyD/Picsart-25-12-27-22-58-29-156.png"
    if 26 <= level <= 30: return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    if 31 <= level <= 35: return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    if 36 <= level <= 38: return "https://i.ibb.co/Q3dnYKDD/Picsart-25-12-27-22-58-41-773.png"
    if 39 <= level <= 44: return "https://i.ibb.co/Kpt81h1w/Picsart-25-12-27-22-58-48-613.png"
    if 45 <= level <= 49: return "https://i.ibb.co/xtxVmgN3/Picsart-25-12-27-22-58-53-180.png"
    if level >= 50: return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"
    return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"

class RankBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ نظام الرتب متصل وجاهز!")

bot = RankBot()

# --- أمر الـ Rank الاحترافي ---
@bot.tree.command(name="rank", description="عرض بطاقة المستوى والرتبة الخاصة بك")
async def rank(interaction: discord.Interaction):
    await interaction.response.defer()
    
    uid = str(interaction.user.id)
    # جلب بيانات المستخدم أو إنشاء بيانات جديدة إذا كان أول مرة
    user_data = db["users"].get(uid, {"xp": 0, "level": 0})
    
    current_xp = user_data["xp"]
    current_lvl = user_data["level"]
    
    # تصميم الإمبد (Embed)
    embed = discord.Embed(
        title=f"📊 بطاقة رتبة | {interaction.user.display_name}",
        color=0x2ecc71
    )
    
    # إضافة الحقول مع صور الأيقونات التي طلبتها
    embed.add_field(
        name="المستوى الحالي", 
        value=f"**Level: {current_lvl}**", 
        inline=True
    )
    embed.add_field(
        name="نقاط الخبرة", 
        value=f"**XP: {current_xp}**", 
        inline=True
    )
    
    # تعيين صورة المستخدم وصورة الرتبة
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=get_rank_image(current_lvl))
    
    # تذييل يحتوي على أيقونات LVL و XP
    embed.set_footer(text="نظام رتب Sky Data", icon_url="https://i.ibb.co/BHy8Kj71/Picsart-25-12-27-23-06-04-733.png")

    await interaction.followup.send(embed=embed)

# --- نظام كسب الـ XP وتخزين البيانات ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    if uid not in db["users"]:
        db["users"][uid] = {"xp": 0, "level": 0}
    
    # إضافة نقاط عشوائية بين 5 و 15 عند كل رسالة
    db["users"][uid]["xp"] += random.randint(5, 15)
    
    # معادلة الترقية (كل 200 نقطة مستوى جديد)
    needed_xp = (db["users"][uid]["level"] + 1) * 200
    if db["users"][uid]["xp"] >= needed_xp:
        db["users"][uid]["level"] += 1
        # تنبيه اختياري عند الترقية
        try:
            await message.channel.send(f"🎊 مبروك {message.author.mention}! ارتقيت للمستوى {db['users'][uid]['level']}")
        except: pass
        
    save_db(db) # حفظ البيانات فوراً في الملف
    await bot.process_commands(message)

# --- واجهة الـ API للموقع ---
app = Flask(__name__)
CORS(app)

@app.route('/api/full_stats')
def full_stats():
    # ترتيب المستخدمين حسب الـ XP لعرض التوب 10
    top_list = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    return jsonify({
        "members": len(db["users"]),
        "top_users": top_list,
        "online": 14 # يمكنك برمجتها لجلب المتصلين حقيقياً
    })

def run_api():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_api).start()
    bot.run(TOKEN)
