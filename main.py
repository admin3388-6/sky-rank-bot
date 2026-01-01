import discord
from discord.ext import commands
from discord import app_commands
import os, json, random, asyncio
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread

# --- إعدادات قاعدة البيانات والتخزين ---
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

# --- دالة جلب الصور بناءً على المستوى الدقيق ---
def get_rank_image(level):
    if 0 <= level <= 2: return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    if 3 <= level <= 5: return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    if 6 <= level <= 8: return "https://i.ibb.co/fztgZ8hG/Picsart-25-12-27-22-57-38-916.png"
    if 9 <= level <= 10: return "https://i.ibb.co/rfy0BDn6/Picsart-25-12-27-22-58-03-096.png"
    if 11 <= level <= 13: return "https://i.ibb.co/Wvfqm8v5/Picsart-25-12-27-22-58-10-424.png"
    if 14 <= level <= 15: return "https://i.ibb.co/0Rrpz67D/Picsart-25-12-27-22-58-15-557.png"
    if 16 <= level <= 20: return "https://i.ibb.co/hx51cSSB/Picsart-25-12-27-22-58-24-170.png"
    if 21 <= level <= 25: return "https://i.ibb.co/tpsztsyD/Picsart-25-12-27-22-58-29-156.png"
    if 26 <= level <= 35: return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    if 36 <= level <= 38: return "https://i.ibb.co/Q3dnYKDD/Picsart-25-12-27-22-58-41-773.png"
    if 39 <= level <= 44: return "https://i.ibb.co/Kpt81h1w/Picsart-25-12-27-22-58-48-613.png"
    if 45 <= level <= 49: return "https://i.ibb.co/xtxVmgN3/Picsart-25-12-27-22-58-53-180.png"
    if level >= 50: return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"
    return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"

class SkyRankBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        # لمسح أي تضارب: نقوم بمزامنة الأوامر عالمياً وللسيرفرات
        print("🔄 جاري مزامنة الأوامر الفورية...")
        await self.tree.sync()
        print("✅ تم تحديث الأوامر بنجاح!")

bot = SkyRankBot()

# --- أمر الرتبة المطور ---
@bot.tree.command(name="rank", description="عرض بطاقة تفاعلك ومستواك في Sky Data")
async def rank(interaction: discord.Interaction):
    # استخدام defer لتفادي خطأ Outdated Command
    await interaction.response.defer()
    
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0})
    
    embed = discord.Embed(
        title=f"📊 بطاقة رتبة {interaction.user.display_name}",
        color=0x00d2ff
    )
    
    # إضافة الصور التي طلبتها كأيقونات للحقول
    lvl_icon = "https://i.ibb.co/0RR5NMP7/Picsart-25-12-27-23-06-27-356.png"
    xp_icon = "https://i.ibb.co/BHy8Kj71/Picsart-25-12-27-23-06-04-733.png"
    
    embed.add_field(name="المستوى", value=f"⭐ **{u['level']}**", inline=True)
    embed.add_field(name="الخبرة", value=f"🧩 **{u['xp']}**", inline=True)
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=get_rank_image(u["level"]))
    
    # تذييل الصفحة يحتوي على الأيقونات المطلوبة
    embed.set_footer(text="Sky Data Elite System", icon_url=xp_icon)
    
    await interaction.followup.send(embed=embed)

# --- نظام تسجيل التفاعل (تخزين التقدم) ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    if uid not in db["users"]:
        db["users"][uid] = {"xp": 0, "level": 0}
    
    # إضافة نقاط خبرة عشوائية
    db["users"][uid]["xp"] += random.randint(5, 15)
    
    # معادلة الترقية: كلما زاد المستوى زادت النقاط المطلوبة
    level_up_xp = (db["users"][uid]["level"] + 1) * 150
    if db["users"][uid]["xp"] >= level_up_xp:
        db["users"][uid]["level"] += 1
        # تنبيه بسيط للترقية
        try:
            await message.channel.send(f"🎊 كفو {message.author.mention}! ارتقيت للمستوى {db['users'][uid]['level']}", delete_after=5)
        except: pass
    
    save_db(db) # حفظ التقدم في database.json
    await bot.process_commands(message)

# --- واجهة الموقع لـ Discord.html ---
app = Flask(__name__)
CORS(app)

@app.route('/api/full_stats')
def full_stats():
    top_users = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    return jsonify({
        "members": len(db["users"]),
        "top_users": top_users,
        "servers": 1,
        "online": 14 
    })

def run_api():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_api).start()
    bot.run(TOKEN)
