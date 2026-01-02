import discord
from discord.ext import commands
from discord import app_commands
import os, random, asyncio, requests, time
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from datetime import datetime, timedelta

# --- 1. الإعدادات والربط (البيانات الأصلية كاملة) ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"]
collection = db["rank_system"]
track_col = db["rank_tracking"] # لنظام الأسهم (صعود/هبوط)

UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213
OWNER_ID = 1429183440485486679 
ADMIN_ROLES = [1448639184532144128, 1448638848098631881, 1448638848090509381]

LEVEL_ROLES = {
    10: 1448821273756172348, 
    20: 1448821177605947402,
    30: 1448821103391674398, 
    40: 1448821022462709891, 
    50: 1448820918490239027
}

# صور الرتب حسب المستويات (الروابط الجديدة)
RANK_IMAGES = {
    50: "https://i.ibb.co/57wV2SH/lv50.webp",
    40: "https://i.ibb.co/ds0DXYjv/lv40.webp",
    30: "https://i.ibb.co/Ng1Zygy1/lv30.webp",
    20: "https://i.ibb.co/cK5Z3ZgC/lv20.webp",
    10: "https://i.ibb.co/0Rb0R6cw/lv10.webp",
    5: "https://i.ibb.co/fV7n1685/lv5.webp"
}

# صور الأيقونات الثابتة للنصوص
ICONS = {
    "level": "https://i.ibb.co/cBwBDbd/lvlicon-193x70p.png",
    "name": "https://i.ibb.co/kgQGjj36/nameicon-193x70.png",
    "xp": "https://i.ibb.co/whbnGb0H/xpicon-110x59p.png"
}

# متجر الخلفيات (كامل كما هو)
STORE_BG = {
    "1": {"url": "https://i.ibb.co/4nXX8y2z/fc17d0243302d37f7759059464e4404a.jpg", "price": 500, "name": "البنفسج الكلاسيكي", "color": "white"},
    "2": {"url": "https://i.ibb.co/XxPBFPGy/74f8c5c8bebb711f0f92cef313ffb6d4.jpg", "price": 700, "name": "البنفسج المظلم", "color": "white"},
    "3": {"url": "https://i.ibb.co/ccKQVm0M/0e3fc888eadfa22b852b1437419e548e.jpg", "price": 1000, "name": "ليالي البنفسج", "color": "white"},
    "4": {"url": "https://i.ibb.co/PZNCzQS8/9d1247f8c186708963115d9ba0bc8977.jpg", "price": 6000, "name": "الأزرق الملكي", "color": "#00E5FF"},
    "5": {"url": "https://i.ibb.co/sJMs2NdR/e0bd76c09d1751a305830eb0fcec27d8.jpg", "price": 2000, "name": "فضاء أزرق", "color": "white"},
    "6": {"url": "https://i.ibb.co/JRjYbkrr/b59066e9e3a0619e8069aa6d35ba994d.jpg", "price": 10000, "name": "النخبة البنفسجية", "color": "white"},
    "7": {"url": "https://i.ibb.co/67krxH9W/eee9b34948a2f314cae78f8dd0e3e70a.jpg", "price": 50000, "name": "الأبيض النقي", "color": "black"},
    "8": {"url": "https://i.ibb.co/gLVXvKpv/ece77d283b543be1824380cacab2ac64.jpg", "price": 7000, "name": "الرخام الأسود", "color": "white"},
    "9": {"url": "https://i.ibb.co/Ld4xZfWh/1368816d0d44c6d4a0911262fcc69df0.jpg", "price": 16000, "name": "أحمر دموي", "color": "white"},
    "16": {"url": "https://i.ibb.co/tPFJ2FTz/01d8d2d501f37741d7702c70fafba4ef.jpg", "price": 1000000, "name": "التاج الأبيض", "color": "black"}
}

DEFAULT_BG = "https://i.ibb.co/4nXX8y2z/fc17d0243302d37f7759059464e4404a.jpg"
xp_cooldown = {}

# --- 2. الدوال المساعدة ونظام الرسم المتطور ---
def format_num(n):
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def get_user(uid):
    u = collection.find_one({"_id": str(uid)})
    if not u:
        u = {"_id": str(uid), "xp": 0, "level": 0, "bg": DEFAULT_BG, "t_color": "white", "msg_count": 0, "start_time": time.time()}
        collection.insert_one(u)
    return u

async def fetch_img(url):
    res = requests.get(url, timeout=10)
    return Image.open(BytesIO(res.content)).convert("RGBA")

def get_rank_badge(lvl):
    for threshold in sorted(RANK_IMAGES.keys(), reverse=True):
        if lvl >= threshold: return RANK_IMAGES[threshold]
    return RANK_IMAGES[5]

async def generate_card(user_data, member):
    try:
        # تحميل الخلفية والأيقونات
        bg_url = user_data.get('bg', DEFAULT_BG)
        base = (await fetch_img(bg_url)).resize((950, 350))
        
        name_bar = (await fetch_img(ICONS["name"])).resize((280, 85))
        lvl_bar = (await fetch_img(ICONS["level"])).resize((280, 85))
        xp_bar = (await fetch_img(ICONS["xp"])).resize((180, 75))
        rank_badge = (await fetch_img(get_rank_badge(user_data['level']))).resize((130, 130))
        
        # الأفاتار الدائري
        av_res = requests.get(member.display_avatar.url)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((210, 210))
        mask = Image.new("L", (210, 210), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 210, 210), fill=255)
        
        # تركيب العناصر
        base.paste(av, (40, 70), mask)
        base.paste(name_bar, (300, 45), name_bar)
        base.paste(lvl_bar, (300, 140), lvl_bar)
        base.paste(xp_bar, (300, 235), xp_bar)
        base.paste(rank_badge, (770, 45), rank_badge)
        
        # رسم النصوص
        draw = ImageDraw.Draw(base)
        t_color = user_data.get('t_color', 'white')
        draw.text((410, 72), f"{member.display_name[:14].upper()}", fill=t_color, stroke_width=2, stroke_fill="black")
        draw.text((410, 168), f"LEVEL: {user_data['level']}", fill=t_color, stroke_width=2, stroke_fill="black")
        draw.text((410, 260), f"XP: {format_num(user_data['xp'])}", fill=t_color, stroke_width=2, stroke_fill="black")

        buf = BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Drawing Error: {e}")
        return None

# --- 3. إعدادات البوت والقفل ---
class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = SkyBot()

def is_staff(it: discord.Interaction):
    return it.user.id == OWNER_ID or any(r.id in ADMIN_ROLES for r in it.user.roles)

async def check_channel(it: discord.Interaction):
    if it.channel_id != ALLOWED_RANK_CH_ID:
        await it.response.send_message(f"❌ مسموح فقط في <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
        return False
    return True

# --- 4. الأوامر التفاعلية (كاملة وبدون نقص) ---
@bot.tree.command(name="rank", description="عرض بطاقتك الصورية الضخمة مع الرتبة")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if not await check_channel(it): return
    await it.response.defer()
    target = member or it.user
    if target.bot: return await it.followup.send("❌ البوتات لا تشارك في النظام.")
    
    u = get_user(target.id)
    card = await generate_card(u, target)
    if card:
        await it.followup.send(file=discord.File(card, f"rank_{target.id}.png"))
    else:
        await it.followup.send("❌ فشل إنشاء البطاقة.")

@bot.tree.command(name="store", description="متجر الخلفيات مع المعاينة")
async def store(it: discord.Interaction):
    if not await check_channel(it): return
    emb = discord.Embed(title="🛒 متجر Sky Data", description="تصفح الخلفيات والمعاينة بالروابط:", color=0x9b59b6)
    for k, v in STORE_BG.items():
        emb.add_field(name=f"الرقم: {k} - {v['name']}", value=f"السعر: `{format_num(v['price'])}` XP\n[رابط المعاينة]({v['url']})", inline=False)
    await it.response.send_message(embed=emb)

@bot.tree.command(name="buy", description="شراء مظهر جديد")
async def buy(it: discord.Interaction, number: str):
    if not await check_channel(it): return
    if number not in STORE_BG: return await it.response.send_message("❌ هذا الرقم غير موجود.", ephemeral=True)
    u = get_user(it.user.id)
    item = STORE_BG[number]
    if u['xp'] < item['price']: return await it.response.send_message("❌ نقاطك لا تكفي!", ephemeral=True)
    
    collection.update_one({"_id": str(it.user.id)}, {"$inc": {"xp": -item['price']}, "$set": {"bg": item['url'], "t_color": item['color']}})
    await it.response.send_message(f"✅ مبروك! تم تحديث بطاقتك إلى **{item['name']}**.")

@bot.tree.command(name="top", description="قائمة الأساطير مع تتبع الترتيب (⬆️/⬇️)")
async def top(it: discord.Interaction):
    if not await check_channel(it): return
    await it.response.defer()
    all_users = list(collection.find().sort("xp", -1).limit(20))
    emb = discord.Embed(title="🏆 قائمة أساطير Sky Data", color=0xf1c40f)
    desc = ""
    count = 0
    for i, u in enumerate(all_users):
        if count >= 10: break
        m = it.guild.get_member(int(u["_id"]))
        if m and not m.bot:
            count += 1
            # حساب التوجه (السهم)
            old_rank = track_col.find_one({"_id": u["_id"]})
            trend = "🟡"
            if old_rank:
                if count < old_rank['pos']: trend = "⬆️"
                elif count > old_rank['pos']: trend = "⬇️"
            track_col.update_one({"_id": u["_id"]}, {"$set": {"pos": count}}, upsert=True)
            
            desc += f"{trend} **#{count}** | {m.mention} - لفل `{u['level']}` - `{format_num(u['xp'])}` XP\n"
    emb.description = desc
    await it.followup.send(embed=emb)

@bot.tree.command(name="give_xp", description="منح نقاط لمستخدم (إداري)")
async def give_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌ للادارة فقط.", ephemeral=True)
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": amount}}, upsert=True)
    await it.response.send_message(f"✅ تم إضافة `{amount}` نقطة لـ {member.mention}.")

# --- 5. نظام الرسائل، الترقية، وتحليل التفاعل ---
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = str(msg.author.id)
    now_ts = time.time()
    
    # استدعاء بيانات المستخدم
    u = get_user(uid)
    
    # منع السبام (XP كل 25 ثانية)
    if uid in xp_cooldown and datetime.now() < xp_cooldown[uid] + timedelta(seconds=25):
        await bot.process_commands(msg)
        return

    xp_cooldown[uid] = datetime.now()
    new_xp = u['xp'] + random.randint(15, 25)
    new_lvl = min(new_xp // 1000, 50) # أقصى لفل 50
    
    # تحديث البيانات وزيادة عداد الرسائل للتحليل
    collection.update_one({"_id": uid}, {
        "$set": {"xp": new_xp, "level": new_lvl},
        "$inc": {"msg_count": 1}
    })
    
    # نظام الترقية والتحليل
    if new_lvl > u['level']:
        # حساب نسبة الكفاءة %
        time_diff = (now_ts - u.get('start_time', now_ts)) / 60
        msgs = u.get('msg_count', 1)
        efficiency = min(100, int((msgs / (time_diff + 1)) * 10))
        
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch:
            badge_url = get_rank_badge(new_lvl)
            embed = discord.Embed(title="🎊 ارتقاء مستوى جديد!", color=0x00ff00)
            embed.set_thumbnail(url=badge_url)
            embed.add_field(name="المستوى", value=f"**{new_lvl}**", inline=True)
            embed.add_field(name="كفاءة التفاعل", value=f"**{efficiency}%**", inline=True)
            embed.description = f"مبروك {msg.author.mention}! لقد تطورت رتبتك بناءً على نشاطك الأخير."
            await ch.send(embed=embed)
        
        # توزيع الرتب تلقائياً
        if new_lvl in LEVEL_ROLES:
            role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
            if role: 
                try: await msg.author.add_roles(role)
                except: pass
        
        # ريست لبيانات التحليل للفل القادم
        collection.update_one({"_id": uid}, {"$set": {"msg_count": 0, "start_time": now_ts}})

    await bot.process_commands(msg)

# --- 6. التشغيل المستمر ---
app = Flask('')
@app.route('/')
def home(): return "Sky System 3.0 Active"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
