import discord
from discord.ext import commands
from discord import app_commands
import os, json, random, asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread

# --- الإعدادات الفنية ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"

def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except: return {"users": {}, "config": {"bg": ""}}

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- إعداد البوت ---
class SkyDataBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        # تعيين prefix احتياطي بجانب أوامر السلاش
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # القضاء على مشكلة Unknown Integration بمسح شامل
        print("🔄 جاري تنظيف وإعادة مزامنة الأوامر...")
        self.tree.clear_commands(guild=None)
        # مزامنة الأوامر عالمياً (قد تستغرق دقائق لتظهر للجميع)
        await self.tree.sync()
        print("✅ تم التزامن الشامل. إذا لم يظهر /rank، انتظر قليلاً أو أعد تشغيل الديسكورد.")

bot = SkyDataBot()

# --- أمر Rank المحدث ---
@bot.tree.command(name="rank", description="عرض بطاقة مستواك وصورتك")
async def rank(interaction: discord.Interaction):
    # استخدام defer لمنع خطأ "Interaction failed"
    await interaction.response.defer()
    
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0, "messages": 0})
    
    # رابط الصورة بناءً على المستوى (تأكد من الروابط التي وضعتها سابقاً)
    rank_img = "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png" # افتراضية للبداية
    
    embed = discord.Embed(title=f"📊 رتبة {interaction.user.display_name}", color=0x00d2ff)
    embed.add_field(name="المستوى", value=str(u['level']), inline=True)
    embed.add_field(name="الخبرة", value=str(u['xp']), inline=True)
    embed.set_image(url=rank_img)
    
    await interaction.followup.send(embed=embed)

# --- إصلاح واجهة الموقع (Backend API) ---
app = Flask(__name__)
CORS(app)

@app.route('/api/full_stats')
def full_stats():
    guild = bot.guilds[0] if bot.guilds else None
    
    # حل مشكلة undefined: التأكد من إرسال كل المفاتيح التي يتوقعها الـ HTML
    stats = {
        "members": guild.member_count if guild else 0,
        "online": len([m for m in guild.members if m.status != discord.Status.offline]) if guild else 0,
        "servers": len(bot.guilds),
        "channels": [{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels] if guild else [],
        "top_users": sorted(db["users"].items(), key=lambda x: x[1].get('xp', 0), reverse=True)[:10],
        "config": db.get("config", {"bg": ""})
    }
    return jsonify(stats)

@app.route('/api/action', methods=['POST'])
def handle_action():
    data = request.json
    # معالجة إرسال الرسائل من الموقع
    if data.get('type') == 'send':
        channel = bot.get_channel(int(data['channel_id']))
        if channel:
            bot.loop.create_task(channel.send(data['content']))
            return jsonify({"status": "success"})
    return jsonify({"status": "failed"})

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
