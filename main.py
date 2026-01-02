import discord
from discord.ext import commands
from discord import app_commands
import os, random, asyncio, requests
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta

# --- الإعدادات الأساسية ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"]
collection = db["rank_system"]

UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213
OWNER_ID = 1429183440485486679 
ADMIN_ROLES_IDS = [1448639184532144128, 1448638848098631881, 1448638848090509381]

LEVEL_ROLES = {
    10: 1448821273756172348, 20: 1448821177605947402,
    30: 1448821103391674398, 40: 1448821022462709891, 50: 1448820918490239027
}

# --- متجر الخلفيات الكامل ---
STORE_BG = {
    "1": {"url": "https://i.ibb.co/4nXX8y2z/fc17d0243302d37f7759059464e4404a.jpg", "price": 500, "name": "بنفسجي كلاسيك"},
    "2": {"url": "https://i.ibb.co/XxPBFPGy/74f8c5c8bebb711f0f92cef313ffb6d4.jpg", "price": 700, "name": "بنفسجي غامق"},
    "3": {"url": "https://i.ibb.co/ccKQVm0M/0e3fc888eadfa22b852b1437419e548e.jpg", "price": 1000, "name": "بنفسجي نيون"},
    "4": {"url": "https://i.ibb.co/PZNCzQS8/9d1247f8c186708963115d9ba0bc8977.jpg", "price": 6000, "name": "أزرق ليلي"},
    "5": {"url": "https://i.ibb.co/sJMs2NdR/e0bd76c09d1751a305830eb0fcec27d8.jpg", "price": 2000, "name": "أزرق فضاء"},
    "6": {"url": "https://i.ibb.co/JRjYbkrr/b59066e9e3a0619e8069aa6d35ba994d.jpg", "price": 10000, "name": "بنفسجي ملكي"},
    "7": {"url": "https://i.ibb.co/67krxH9W/eee9b34948a2f314cae78f8dd0e3e70a.jpg", "price": 50000, "name": "أزرق جليدي"},
    "8": {"url": "https://i.ibb.co/gLVXvKpv/ece77d283b543be1824380cacab2ac64.jpg", "price": 7000, "name": "أبيض وأسود"},
    "9": {"url": "https://i.ibb.co/Ld4xZfWh/1368816d0d44c6d4a0911262fcc69df0.jpg", "price": 16000, "name": "أحمر دموي"},
    "10": {"url": "https://i.ibb.co/bjm3VMpN/4b9cb08660e3ee8c09fe51a2492b5325.jpg", "price": 8000, "name": "أزرق سماوي"},
    "11": {"url": "https://i.ibb.co/6R15KycG/e150999f4d149dda55e388b20e809d1e.jpg", "price": 10000, "name": "أزرق تقني"},
    "12": {"url": "https://i.ibb.co/TGQYy5g/df3d144da1f68d8e745f5f77285ea905.jpg", "price": 17000, "name": "أحمر ناري"},
    "13": {"url": "https://i.ibb.co/zWBB1dPM/f4c0a71249df58deec8489a9966041b4.jpg", "price": 500, "name": "أصفر مشرق"},
    "14": {"url": "https://i.ibb.co/ZpJdZkyY/efc5eaa9fafda738ea61300fda787db5.jpg", "price": 700, "name": "أحمر كلاسيك"},
    "15": {"url": "https://i.ibb.co/dw1DJH1R/afdb785b3962b75fa2e6afaf63fffc5e.jpg", "price": 14000, "name": "فخامة سوداء"},
    "16": {"url": "https://i.ibb.co/tPFJ2FTz/01d8d2d501f37741d7702c70fafba4ef.jpg", "price": 1000000, "name": "الخلفية الأسطورية"}
}

DEFAULT_BG = "https://i.ibb.co/4nXX8y2z/fc17d0243302d37f7759059464e4404a.jpg"
xp_cooldown = {}

# --- دالة اختصار الأرقام ---
def format_num(n):
    if n >= 1_000_000_000: return f"{n/1e9:.1f}B"
    if n >= 1_000_000: return f"{n/1e6:.1f}M"
    if n >= 1_000: return f"{n/1e3:.1f}K"
    return str(n)

# --- دالة جلب البيانات ---
def get_user(uid):
    u = collection.find_one({"_id": uid})
    if not u:
        u = {"_id": uid, "xp": 0, "level": 0, "bg": DEFAULT_BG}
        collection.insert_one(u)
    return u

# --- دالة صنع بطاقة الرتبة ---
async def generate_rank_card(name, level, xp, avatar_url, bg_url):
    bg_data = requests.get(bg_url).content
    img = Image.open(BytesIO(bg_data)).convert("RGBA").resize((900, 300))
    
    av_data = requests.get(avatar_url).content
    av = Image.open(BytesIO(av_data)).convert("RGBA").resize((180, 180))
    
    mask = Image.new("L", (180, 180), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
    img.paste(av, (50, 60), mask)
    
    draw = ImageDraw.Draw(img)
    try: font_large = ImageFont.truetype("default.ttf", 50)
    except: font_large = ImageFont.load_default()
    
    draw.text((260, 70), f"{name}", fill="white", font=font_large)
    draw.text((260, 140), f"Level: {level}", fill="#bdc3c7", font=font_large)
    draw.text((260, 200), f"XP: {format_num(xp)}", fill="#f1c40f", font=font_large)
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): await self.tree.sync()

bot = SkyBot()

def is_staff(it: discord.Interaction):
    return it.user.id == OWNER_ID or any(r.id in ADMIN_ROLES_IDS for r in it.user.roles)

# --- الأوامر الإدارية ---
@bot.tree.command(name="give_xp", description="إعطاء نقاط لمستخدم")
async def give_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌ للادارة فقط", ephemeral=True)
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": amount}}, upsert=True)
    await it.response.send_message(f"✅ تم إعطاء {member.mention} {amount} نقطة.")

@bot.tree.command(name="reset_all", description="تصفير السيرفر (للأونر)")
async def reset_all(it: discord.Interaction):
    if it.user.id != OWNER_ID: return await it.response.send_message("❌ للأونر فقط", ephemeral=True)
    collection.delete_many({})
    await it.response.send_message("⚠️ تم تصفير جميع البيانات بنجاح.")

# --- الأوامر العامة ---
@bot.tree.command(name="rank", description="عرض بطاقتك الصورية")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if it.channel_id != ALLOWED_RANK_CH_ID:
        return await it.response.send_message(f"❌ استخدم <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
    await it.response.defer()
    target = member or it.user
    u = get_user(str(target.id))
    card = await generate_rank_card(target.display_name, u['level'], u['xp'], target.display_avatar.url, u.get('bg', DEFAULT_BG))
    await it.followup.send(file=discord.File(card, "rank.png"))

@bot.tree.command(name="store", description="متجر الخلفيات")
async def store(it: discord.Interaction):
    emb = discord.Embed(title="🛒 متجر خلفيات Sky", color=0x9b59b6)
    for k, v in STORE_BG.items():
        emb.add_field(name=f"رقم {k}", value=f"السعر: {format_num(v['price'])} XP\n{v['name']}", inline=True)
    await it.response.send_message(embed=emb)

@bot.tree.command(name="buy", description="شراء خلفية بالنقاط")
async def buy(it: discord.Interaction, number: str):
    if number not in STORE_BG: return await it.response.send_message("❌ رقم خاطئ")
    u = get_user(str(it.user.id))
    item = STORE_BG[number]
    if u['xp'] < item['price']: return await it.response.send_message("❌ نقاطك لا تكفي")
    collection.update_one({"_id": str(it.user.id)}, {"$inc": {"xp": -item['price']}, "$set": {"bg": item['url']}})
    await it.response.send_message(f"✅ اشتريت {item['name']} بنجاح!")

@bot.tree.command(name="top", description="المتصدرين")
async def top(it: discord.Interaction):
    await it.response.defer()
    users = list(collection.find().sort("xp", -1).limit(10))
    emb = discord.Embed(title="🏆 أساطير Sky Data", color=0xf1c40f)
    desc = ""
    for i, u in enumerate(users, 1):
        m = it.guild.get_member(int(u["_id"]))
        name = m.mention if m else "غادر"
        desc += f"**#{i}** | {name} - لفل `{u['level']}` - `{format_num(u['xp'])}` XP\n"
    emb.description = desc
    await it.followup.send(embed=emb)

# --- نظام الـ XP والترقيات ---
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = str(msg.author.id)
    now = datetime.now()
    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=30): return
    
    u = get_user(uid)
    new_xp = u['xp'] + random.randint(15, 25)
    new_lvl = new_xp // 250
    xp_cooldown[uid] = now
    
    collection.update_one({"_id": uid}, {"$set": {"xp": new_xp, "level": new_lvl}})
    
    if new_lvl > u['level']:
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch: 
            e = discord.Embed(title="🆙 لفل جديد!", description=f"مبروك {msg.author.mention} لفل {new_lvl}", color=0x2ecc71)
            await ch.send(embed=e)
        if new_lvl in LEVEL_ROLES:
            role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
            if role: await msg.author.add_roles(role)
    await bot.process_commands(msg)

# --- تشغيل السيرفر ---
app = Flask('')
@app.route('/')
def home(): return "Sky System Online"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
