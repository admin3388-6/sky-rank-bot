import discord
from discord.ext import commands
from discord import app_commands
import os, random, asyncio, requests
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from datetime import datetime, timedelta

# --- 1. الإعدادات والربط ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"]
collection = db["rank_system"]

# قنوات التنبيه والرتب
UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213
OWNER_ID = 1429183440485486679 
ADMIN_ROLES = [1448639184532144128, 1448638848098631881, 1448638848090509381]

# نظام الرتب التلقائي (مستوى : آيدي الرتبة)
LEVEL_ROLES = {
    10: 1448821273756172348, 
    20: 1448821177605947402,
    30: 1448821103391674398, 
    40: 1448821022462709891, 
    50: 1448820918490239027
}

# --- 2. متجر الخلفيات الكامل ---
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

# --- 3. الدوال المساعدة ونظام الرسم ---
def format_num(n):
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def get_user(uid):
    u = collection.find_one({"_id": str(uid)})
    if not u:
        u = {"_id": str(uid), "xp": 0, "level": 0, "bg": DEFAULT_BG, "t_color": "white"}
        collection.insert_one(u)
    return u

async def generate_card(name, level, xp, avatar_url, bg_url, text_color):
    try:
        # تحميل الموارد
        bg_res = requests.get(bg_url, timeout=10)
        img = Image.open(BytesIO(bg_res.content)).convert("RGBA").resize((900, 300))
        
        av_res = requests.get(avatar_url, timeout=10)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((200, 200))
        
        # قناع دائري للأفاتار
        mask = Image.new("L", (200, 200), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
        img.paste(av, (40, 50), mask)
        
        # طبقة النص لضمان أعلى جودة ومنع التشويش
        txt_layer = Image.new("RGBA", (900, 300), (0,0,0,0))
        draw = ImageDraw.Draw(txt_layer)
        
        # دالة الرسم العملاق (أكبر بـ 60% مع تنعيم)
        def draw_massive_text(pos, text, color):
            x, y = pos
            outline = "black" if color != "black" else "white"
            # رسم حدود النص (Stroke) لزيادة الوضوح
            for i in range(-4, 5):
                for j in range(-4, 5):
                    draw.text((x+i, y+j), text, fill=outline)
            # رسم النص الأساسي بطبقات متعددة لزيادة الحجم والوضوح
            for offset in [0, 0.5, 1]:
                draw.text((x+offset, y), text, fill=color)

        # مواقع النصوص الضخمة
        draw_massive_text((270, 40), f"{name.upper()}", text_color)
        draw_massive_text((270, 120), f"LEVEL: {level}", text_color)
        draw_massive_text((270, 200), f"TOTAL XP: {format_num(xp)}", text_color)
        
        combined = Image.alpha_composite(img, txt_layer)
        buf = BytesIO()
        combined.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Drawing Error: {e}")
        return None

# --- 4. إعدادات البوت ---
class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = SkyBot()

def is_staff(it: discord.Interaction):
    return it.user.id == OWNER_ID or any(r.id in ADMIN_ROLES for r in it.user.roles)

# --- 5. الأوامر التفاعلية ---
@bot.tree.command(name="rank", description="عرض بطاقتك الصورية الضخمة")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if it.channel_id != ALLOWED_RANK_CH_ID:
        return await it.response.send_message(f"❌ استخدم الروم <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
    
    await it.response.defer()
    target = member or it.user
    if target.bot: return await it.followup.send("❌ البوتات لا تشارك في النظام.")
    
    u = get_user(target.id)
    card = await generate_card(target.display_name, u['level'], u['xp'], target.display_avatar.url, u['bg'], u['t_color'])
    
    if card:
        await it.followup.send(file=discord.File(card, f"rank_{target.id}.png"))
    else:
        await it.followup.send("❌ فشل إنشاء البطاقة، جرب مرة أخرى.")

@bot.tree.command(name="store", description="متجر الخلفيات")
async def store(it: discord.Interaction):
    emb = discord.Embed(title="🛒 متجر Sky Data", description="شراء الخلفية يغير شكل بطاقة `/rank`", color=0x9b59b6)
    for k, v in STORE_BG.items():
        emb.add_field(name=f"الرقم: {k}", value=f"**{v['name']}**\nالسعر: `{format_num(v['price'])}` XP", inline=True)
    await it.response.send_message(embed=emb)

@bot.tree.command(name="buy", description="شراء مظهر جديد")
async def buy(it: discord.Interaction, number: str):
    if number not in STORE_BG: return await it.response.send_message("❌ هذا الرقم غير موجود.", ephemeral=True)
    u = get_user(it.user.id)
    item = STORE_BG[number]
    if u['xp'] < item['price']: return await it.response.send_message("❌ نقاطك لا تكفي!", ephemeral=True)
    
    collection.update_one({"_id": str(it.user.id)}, {"$inc": {"xp": -item['price']}, "$set": {"bg": item['url'], "t_color": item['color']}})
    await it.response.send_message(f"✅ مبروك! تم تحديث بطاقتك إلى **{item['name']}**.")

@bot.tree.command(name="top", description="قائمة الأساطير (بدون بوتات)")
async def top(it: discord.Interaction):
    await it.response.defer()
    all_users = list(collection.find().sort("xp", -1).limit(50))
    emb = discord.Embed(title="🏆 قائمة أساطير Sky Data", color=0xf1c40f)
    desc = ""
    count = 0
    for u in all_users:
        if count >= 10: break
        m = it.guild.get_member(int(u["_id"]))
        if m and not m.bot:
            count += 1
            desc += f"**#{count}** | {m.mention} - لفل `{u['level']}` - `{format_num(u['xp'])}` XP\n"
    emb.description = desc
    await it.followup.send(embed=emb)

@bot.tree.command(name="give_xp", description="منح نقاط لمستخدم (إداري)")
async def give_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌ للادارة فقط.", ephemeral=True)
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": amount}}, upsert=True)
    await it.response.send_message(f"✅ تم إضافة `{amount}` نقطة لـ {member.mention}.")

# --- 6. نظام الرسائل والتلقائيات ---
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = str(msg.author.id)
    now = datetime.now()
    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=20): return
    
    u = get_user(uid)
    new_xp = u['xp'] + random.randint(15, 25)
    new_lvl = new_xp // 250
    xp_cooldown[uid] = now
    
    collection.update_one({"_id": uid}, {"$set": {"xp": new_xp, "level": new_lvl}})
    
    if new_lvl > u['level']:
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch: await ch.send(f"🎊 {msg.author.mention} مبروك ارتقيت للفل **{new_lvl}**!")
        if new_lvl in LEVEL_ROLES:
            role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
            if role: 
                try: await msg.author.add_roles(role)
                except: pass
    await bot.process_commands(msg)

# --- 7. استمرارية العمل ---
app = Flask('')
@app.route('/')
def home(): return "Sky System 2.0 Active"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
