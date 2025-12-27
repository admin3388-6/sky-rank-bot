import discord
from discord.ext import commands
from discord import app_commands
import os, io, requests, asyncio, json, random
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
from datetime import timedelta

# --- الإعدادات الفنية الكاملة ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"
IP_CHANNEL_ID = 1448805638686769213

# صور الأيقونات الثابتة
XP_ICON_URL = "https://i.ibb.co/BHy8Kj71/Picsart-25-12-27-23-06-04-733.png"
LVL_ICON_URL = "https://i.ibb.co/0RR5NMP7/Picsart-25-12-27-23-06-27-356.png"

# --- قاعدة بيانات الرتب ---
def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except: 
        return {
            "users": {}, 
            "config": {
                "welcome_ch": None, 
                "bg": "https://i.ibb.co/mVYpF4RQ/Picsart-25-12-24-14-57-39-769.jpg", 
                "anti_spam": True,
                "smart_reply_enabled": True
            }
        }

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- دالة جلب صورة الرتبة بناءً على المستوى ---
def get_rank_image(level):
    if 0 <= level <= 2:
        return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    elif 3 <= level <= 5:
        return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    elif 6 <= level <= 8:
        return "https://i.ibb.co/fztgZ8hG/Picsart-25-12-27-22-57-38-916.png"
    elif 9 <= level <= 10:
        return "https://i.ibb.co/rfy0BDn6/Picsart-25-12-27-22-58-03-096.png"
    elif 11 <= level <= 13:
        return "https://i.ibb.co/Wvfqm8v5/Picsart-25-12-27-22-58-10-424.png"
    elif 14 <= level <= 15:
        return "https://i.ibb.co/0Rrpz67D/Picsart-25-12-27-22-58-15-557.png"
    elif 16 <= level <= 20:
        return "https://i.ibb.co/hx51cSSB/Picsart-25-12-27-22-58-24-170.png"
    elif 21 <= level <= 25:
        return "https://i.ibb.co/tpsztsyD/Picsart-25-12-27-22-58-29-156.png"
    elif 26 <= level <= 35: # تم دمج الفئات المتشابهة حسب طلبك
        return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    elif 36 <= level <= 38:
        return "https://i.ibb.co/Q3dnYKDD/Picsart-25-12-27-22-58-41-773.png"
    elif 39 <= level <= 44:
        return "https://i.ibb.co/Kpt81h1w/Picsart-25-12-27-22-58-48-613.png"
    elif 45 <= level <= 49:
        return "https://i.ibb.co/xtxVmgN3/Picsart-25-12-27-22-58-53-180.png"
    elif level >= 50:
        return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"
    return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"

# --- إعداد البوت ---
class SkyDataBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ تم تزامن أوامر السلاش بنجاح")

bot = SkyDataBot()

# --- نظام الردود الذكية (كاملاً) ---
SMART_REPLIES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته، يا هلا بك نورتنا!",
    "سلام": "يا هلا والله، وعليكم السلام والرحمة، كيف حالك؟",
    "صباح الخير": "صباح النور والسرور، يسعد صباحك يا وحش!",
    "مساء الخير": "مساء الورد والجمال، حياك الله في سيرفرنا.",
    "شخبارك": "بخير عساك بخير، أنت وش علومك وطمنا عنك؟",
    "كيفك": "الحمد لله تمام، جعل أيامك كلها سعادة وفرح.",
    "منور": "النور نورك يا غالي، السيرفر منور بوجودك فيه.",
    "ip": "تفضل الأي بي يا بطل: `sd2k.progamer.me` 🎮",
    "اي بي": "تفضل الأي بي يا بطل: `sd2k.progamer.me` 🎮",
    "ارحب": "تبقى وتسلم، ترحيبة المطر!",
    "شكرا": "العفو، هذا أقل واجب نقدمه لك يا طيب!",
    "كفو": "كفوك الطيب، أنت أصل الفخر والعز."
}

# --- معالجة XP ---
async def process_xp(user):
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"xp": 0, "level": 0, "messages": 0}
    
    u = db["users"][uid]
    u["xp"] += random.randint(15, 25)
    u["messages"] += 1
    
    # معادلة المستوى الاحترافية
    next_level_xp = int(150 * (u["level"] ** 1.8) + 100)
    
    if u["xp"] >= next_level_xp and u["level"] < 50:
        u["level"] += 1
        save_db(db)
        return True
    save_db(db)
    return False

# --- أوامر السلاش المحسنة ---
@bot.tree.command(name="rank", description="عرض بطاقة مستواك وصورة رتبتك")
async def rank(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0, "messages": 0})
    
    level = u["level"]
    xp = u["xp"]
    rank_img = get_rank_image(level)
    next_xp = int(150 * (level ** 1.8) + 100)

    embed = discord.Embed(
        title=f"📊 بطاقة مستوى | {interaction.user.display_name}",
        color=0x00d2ff
    )
    
    # إضافة صورة المستخدم وصورة الرتبة
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=rank_img) # صورة الرتبة الكبيرة
    
    # تنسيق الحقول بالأيقونات المطلوبة
    embed.add_field(name=f"⭐ المستوى (Level)", value=f"**{level}**", inline=True)
    embed.add_field(name=f"🧩 نقاط الخبرة (XP)", value=f"**{xp} / {next_xp}**", inline=True)
    
    # إضافة أيقونات صغيرة في الوصف أو الحقول
    embed.description = f"**صورة المستوى:** [اضغط هنا]({LVL_ICON_URL})\n**صورة الخبرة:** [اضغط هنا]({XP_ICON_URL})"
    
    embed.set_footer(text=f"طلب بواسطة: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# --- أحداث البوت ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # إضافة XP
    if await process_xp(message.author):
        # إرسال رسالة ترقية أنيقة
        lvl_img = get_rank_image(db["users"][str(message.author.id)]["level"])
        embed = discord.Embed(
            title="🎊 ترقية جديدة!",
            description=f"كفو {message.author.mention}! لقد وصلت للمستوى **{db['users'][str(message.author.id)]['level']}**",
            color=0x2ecc71
        )
        embed.set_thumbnail(url=lvl_img)
        await message.channel.send(embed=embed)

    # الرد التلقائي
    if message.channel.id == IP_CHANNEL_ID:
        for key, reply in SMART_REPLIES.items():
            if key in message.content:
                await message.reply(reply)
                break

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ البوت متصل باسم: {bot.user}")

# --- تشغيل لوحة التحكم والبوت ---
app = Flask(__name__)
CORS(app)

@app.route('/api/stats')
def stats():
    guild = bot.guilds[0] if bot.guilds else None
    return jsonify({
        "members": guild.member_count if guild else 0,
        "online": len([m for m in guild.members if m.status != discord.Status.offline]) if guild else 0,
        "channels": [{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels],
        "top_users": sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    })

def run_flask(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_flask).start()
bot.run(TOKEN)
