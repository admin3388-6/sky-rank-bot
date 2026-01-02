import discord
from discord.ext import commands
from discord import app_commands
import os, random, asyncio, requests, time, math
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta

# --- 1. الإعدادات والربط وقاعدة البيانات ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"]
collection = db["rank_system"]
track_col = db["rank_tracking"]
config_col = db["bot_config"] # لتخزين حالة الـ Boost

# معرفات القنوات والرتب (كما طلبتها بدقة)
UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213
BOOST_CH_ID = 1456706005575667825
OWNER_ID = 1429183440485486679 
ADMIN_ROLES = [1448639184532144128, 1448638848098631881, 1448638848090509381]

LEVEL_ROLES = {
    10: 1448821273756172348, 20: 1448821177605947402,
    30: 1448821103391674398, 40: 1448821022462709891, 50: 1448820918490239027
}

# نظام الأيقونات المتغيرة (Badges)
RANK_IMAGES = {
    0: "https://i.ibb.co/fV7n1685/lv5.webp",
    10: "https://i.ibb.co/0Rb0R6cw/lv10.webp",
    20: "https://i.ibb.co/cK5Z3ZgC/lv20.webp",
    30: "https://i.ibb.co/Ng1Zygy1/lv30.webp",
    40: "https://i.ibb.co/ds0DXYjv/lv40.webp",
    50: "https://i.ibb.co/57wV2SH/lv50.webp"
}

# المتجر الكامل
STORE_BG = {
    "1": {"url": "https://i.ibb.co/4nXX8y2z/fc17d0243302d37f7759059464e4404a.jpg", "price": 0, "name": "البنفسج الكلاسيكي", "color": "#FFFFFF"},
    "2": {"url": "https://i.ibb.co/XxPBFPGy/74f8c5c8bebb711f0f92cef313ffb6d4.jpg", "price": 700, "name": "البنفسج المظلم", "color": "#E0B0FF"},
    "3": {"url": "https://i.ibb.co/ccKQVm0M/0e3fc888eadfa22b852b1437419e548e.jpg", "price": 1000, "name": "ليالي البنفسج", "color": "#D8BFD8"},
    "4": {"url": "https://i.ibb.co/PZNCzQS8/9d1247f8c186708963115d9ba0bc8977.jpg", "price": 6000, "name": "الأزرق الملكي", "color": "#00E5FF"},
    "5": {"url": "https://i.ibb.co/sJMs2NdR/e0bd76c09d1751a305830eb0fcec27d8.jpg", "price": 2000, "name": "فضاء أزرق", "color": "#87CEEB"},
    "6": {"url": "https://i.ibb.co/JRjYbkrr/b59066e9e3a0619e8069aa6d35ba994d.jpg", "price": 10000, "name": "النخبة البنفسجية", "color": "#DA70D6"},
    "7": {"url": "https://i.ibb.co/67krxH9W/eee9b34948a2f314cae78f8dd0e3e70a.jpg", "price": 50000, "name": "الأبيض النقي", "color": "#000000"},
    "8": {"url": "https://i.ibb.co/gLVXvKpv/ece77d283b543be1824380cacab2ac64.jpg", "price": 7000, "name": "الرخام الأسود", "color": "#FFFFFF"},
    "9": {"url": "https://i.ibb.co/Ld4xZfWh/1368816d0d44c6d4a0911262fcc69df0.jpg", "price": 16000, "name": "أحمر دموي", "color": "#FF0000"},
    "16": {"url": "https://i.ibb.co/tPFJ2FTz/01d8d2d501f37741d7702c70fafba4ef.jpg", "price": 1000000, "name": "التاج الأبيض", "color": "#FFD700"}
}

xp_cooldown = {}

# --- 2. محركات النظام (XP والمستويات) ---

# نظام المستويات التصاعدي: xp = 1000 * (1.2 ^ current_level)
def get_xp_for_level(level):
    if level <= 0: return 0
    return int(1000 * (1.2 ** (level - 1)))

# نظام K, M, B لتقليل الفوضى
def format_num(n):
    if n >= 1e9: return f"{n/1e9:.1f}B"
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

async def fetch_img(url):
    res = requests.get(url, timeout=5)
    return Image.open(BytesIO(res.content)).convert("RGBA")

def get_font(size):
    try: return ImageFont.truetype("arial.ttf", size)
    except: return ImageFont.load_default()

# --- 3. محرك رسم بطاقة الرانك ---
async def generate_card(user_data, member):
    try:
        bg_id = user_data.get('bg_id', "1")
        bg_info = STORE_BG.get(bg_id, STORE_BG["1"])
        
        base = (await fetch_img(bg_info['url'])).resize((950, 350))
        draw = ImageDraw.Draw(base)

        # الأفاتار
        av_res = requests.get(member.display_avatar.url, timeout=5)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((220, 220))
        mask = Image.new("L", (220, 220), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 220, 220), fill=255)
        
        draw.ellipse((40, 55, 280, 295), fill=bg_info['color'])
        base.paste(av, (50, 65), mask)

        # النصوص
        f_huge, f_name, f_sub = get_font(80), get_font(55), get_font(35)
        draw.text((320, 45), f"{member.display_name[:14]}", fill="white", font=f_name, stroke_width=3, stroke_fill="black")
        
        draw.text((320, 135), "LEVEL", fill="white", font=f_sub, stroke_width=2, stroke_fill="black")
        draw.text((320, 180), f"{user_data['level']}", fill=bg_info['color'], font=f_huge, stroke_width=4, stroke_fill="black")
        
        draw.text((580, 135), "XP POINTS", fill="white", font=f_sub, stroke_width=2, stroke_fill="black")
        draw.text((580, 180), f"{format_num(user_data['xp'])}", fill=bg_info['color'], font=f_huge, stroke_width=4, stroke_fill="black")

        # الشارة (الأيقونة) المتغيرة تلقائياً
        lvl = user_data['level']
        # جلب أعلى أيقونة وصل لها العضو
        current_badge_key = max([k for k in RANK_IMAGES.keys() if k <= lvl])
        badge_url = RANK_IMAGES[current_badge_key]
        badge = (await fetch_img(badge_url)).resize((175, 175))
        base.paste(badge, (750, 85), badge)

        buf = BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Drawing Error: {e}")
        return None

# --- 4. إعدادات البوت والأوامر ---
class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): await self.tree.sync()

bot = SkyBot()

def is_admin(it: discord.Interaction):
    return it.user.id == OWNER_ID or any(r.id in ADMIN_ROLES for r in it.user.roles)

# --- نظام الـ Boost (X2) ---
@bot.tree.command(name="boost", description="تفعيل مضاعفة النقاط X2 (للمالك فقط)")
async def boost(it: discord.Interaction, minutes: int):
    if it.user.id != OWNER_ID: return await it.response.send_message("❌ هذا الأمر للمالك فقط.", ephemeral=True)
    
    end_time = datetime.now() + timedelta(minutes=minutes)
    config_col.update_one({"_id": "boost"}, {"$set": {"active": True, "end": end_time.timestamp()}}, upsert=True)
    
    ch = bot.get_channel(BOOST_CH_ID)
    if ch:
        await ch.send(f"@everyone\n🚀 **تعزيز النقاط نشط الآن (XP X2)!**\n⏰ المدة: **{minutes} دقيقة**\nغرفة التعزيز: <#{BOOST_CH_ID}>")
    
    await it.response.send_message(f"✅ تم تفعيل البوست بنجاح لمدة {minutes} دقيقة.")

# --- أوامر الرانك والمخزون والتجهيز ---
@bot.tree.command(name="rank", description="عرض بطاقتك")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if it.channel_id != ALLOWED_RANK_CH_ID: return await it.response.send_message("❌ الروم غلط.", ephemeral=True)
    await it.response.defer()
    target = member or it.user
    u = collection.find_one({"_id": str(target.id)}) or {"_id": str(target.id), "xp": 0, "level": 0, "bg_id": "1", "inventory": ["1"]}
    card = await generate_card(u, target)
    if card: await it.followup.send(file=discord.File(card, "rank.png"))

@bot.tree.command(name="inventory", description="خلفياتك المملوكة")
async def inventory(it: discord.Interaction):
    u = collection.find_one({"_id": str(it.user.id)}) or {"inventory": ["1"], "bg_id": "1"}
    inv = u.get("inventory", ["1"])
    current = u.get("bg_id", "1")
    msg = "🎒 **خلفياتك:**\n"
    for item_id in inv:
        name = STORE_BG.get(item_id, {}).get('name', '؟؟')
        status = "🟢 (مجهز)" if item_id == current else "🔴"
        msg += f"**#{item_id}** | {name} {status}\n"
    await it.response.send_message(msg)

@bot.tree.command(name="equip", description="تجهيز خلفية")
async def equip(it: discord.Interaction, id: str):
    u = collection.find_one({"_id": str(it.user.id)}) or {"inventory": ["1"]}
    if id not in u.get("inventory", ["1"]): return await it.response.send_message("❌ لا تملكها.")
    collection.update_one({"_id": str(it.user.id)}, {"$set": {"bg_id": id}})
    await it.response.send_message(f"✅ تم تجهيز الخلفية رقم #{id}")

# --- أوامر المتجر ---
@bot.tree.command(name="store", description="متجر البانرات")
async def store(it: discord.Interaction):
    u = collection.find_one({"_id": str(it.user.id)}) or {"inventory": ["1"]}
    inv = u.get("inventory", ["1"])
    embeds = []
    for k, v in list(STORE_BG.items()):
        status = "✅ مملوك" if k in inv else f"💰 {format_num(v['price'])} XP"
        emb = discord.Embed(title=f"بانر #{k} - {v['name']}", description=status, color=0x2ecc71 if k in inv else 0xe91e63)
        emb.set_image(url=v['url'])
        embeds.append(emb)
    await it.response.send_message(embeds=embeds[:10]) # ديسكورد يسمح بـ 10 ايمبد في الرسالة

@bot.tree.command(name="buy", description="شراء بانر")
async def buy(it: discord.Interaction, id: str):
    if id not in STORE_BG: return await it.response.send_message("❌ غير موجود.")
    u = collection.find_one({"_id": str(it.user.id)}) or {"xp": 0, "inventory": ["1"]}
    if id in u.get("inventory", ["1"]): return await it.response.send_message("⚠️ عندك إياه.")
    price = STORE_BG[id]['price']
    if u.get('xp', 0) < price: return await it.response.send_message(f"❌ نقاطك {format_num(u.get('xp',0))} ما تكفي.")
    collection.update_one({"_id": str(it.user.id)}, {"$inc": {"xp": -price}, "$push": {"inventory": id}, "$set": {"bg_id": id}})
    await it.response.send_message(f"🎉 تم الشراء بنجاح!")

# --- أوامر الإدارة (كاملة بدون حذف) ---
@bot.tree.command(name="add_xp", description="إضافة XP لعضو")
async def add_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_admin(it): return await it.response.send_message("❌")
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": amount}}, upsert=True)
    await it.response.send_message(f"✅ أضفت {amount} XP لـ {member.mention}")

@bot.tree.command(name="set_level", description="تغيير لفل عضو")
async def set_level(it: discord.Interaction, member: discord.Member, level: int):
    if not is_admin(it): return await it.response.send_message("❌")
    xp = get_xp_for_level(level)
    collection.update_one({"_id": str(member.id)}, {"$set": {"level": level, "xp": xp}}, upsert=True)
    await it.response.send_message(f"✅ صار لفل {member.mention} الآن: {level}")

@bot.tree.command(name="reset_user", description="تصفير بيانات عضو")
async def reset_user(it: discord.Interaction, member: discord.Member):
    if not is_admin(it): return await it.response.send_message("❌")
    collection.delete_one({"_id": str(member.id)})
    await it.response.send_message(f"🗑️ تم تصفير {member.mention}")

@bot.tree.command(name="top", description="المتصدرين")
async def top(it: discord.Interaction):
    await it.response.defer()
    all_u = list(collection.find().sort("xp", -1).limit(10))
    desc = ""
    for i, u in enumerate(all_u, 1):
        m = it.guild.get_member(int(u["_id"]))
        if m:
            old = track_col.find_one({"_id": u["_id"]})
            trend = "🟢" if old and i < old['pos'] else "🔴" if old and i > old['pos'] else "🟡"
            track_col.update_one({"_id": u["_id"]}, {"$set": {"pos": i}}, upsert=True)
            desc += f"{trend} **#{i}** | {m.mention} - لفل `{u['level']}` - `{format_num(u['xp'])}` XP\n"
    await it.followup.send(embed=discord.Embed(title="🏆 قائمة الأساطير", description=desc, color=0xf1c40f))

# --- 5. نظام XP الديناميكي والترقية والبوست ---
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    
    uid = str(msg.author.id)
    content_len = len(msg.content)
    
    # مكافحة السبام (Cooldown ذكي)
    cd = 30 if content_len < 10 else 15
    now = datetime.now()
    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=cd): return
    xp_cooldown[uid] = now

    # XP ديناميكي (عدد الأحرف × 0.5) - بحد أدنى 10 وأقصى 100
    base_xp = max(10, min(100, int(content_len * 0.5)))
    
    # فحص الـ Boost (X2)
    boost_data = config_col.find_one({"_id": "boost"})
    if boost_data and boost_data.get('active') and time.time() < boost_data.get('end', 0):
        base_xp *= 2

    u = collection.find_one({"_id": uid}) or {"_id": uid, "xp": 0, "level": 0, "bg_id": "1", "inventory": ["1"]}
    new_xp = u['xp'] + base_xp
    
    # نظام الترقية التصاعدي
    current_lvl = u['level']
    needed = get_xp_for_level(current_lvl + 1)
    
    if new_xp >= needed:
        new_lvl = current_lvl + 1
        collection.update_one({"_id": uid}, {"$set": {"xp": new_xp, "level": new_lvl}}, upsert=True)
        
        # رسالة الترقية في الروم المخصص
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch:
            emb = discord.Embed(title="🆙 مستوى جديد!", description=f"كفو {msg.author.mention}! وصلت لفل **{new_lvl}** 🎉\nXP القادم: `{format_num(get_xp_for_level(new_lvl+1))}`", color=0x2ecc71)
            emb.set_thumbnail(url=msg.author.display_avatar.url)
            await ch.send(embed=emb)
        
        # إضافة الرتبة التلقائية
        if new_lvl in LEVEL_ROLES:
            role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
            if role: await msg.author.add_roles(role)
    else:
        collection.update_one({"_id": uid}, {"$set": {"xp": new_xp}}, upsert=True)

    await bot.process_commands(msg)

# --- 6. تشغيل السيرفر والبوت ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Running"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
