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

UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213
OWNER_ID = 1429183440485486679 
ADMIN_ROLES = [1448639184532144128, 1448638848098631881, 1448638848090509381]

LEVEL_ROLES = {
    10: 1448821273756172348, 20: 1448821177605947402,
    30: 1448821103391674398, 40: 1448821022462709891, 50: 1448820918490239027
}

STORE_BG = {
    "1": {"url": "https://i.ibb.co/4nXX8y2z/fc17d0243302d37f7759059464e4404a.jpg", "price": 500, "name": "البنفسج الكلاسيكي", "color": "#FFFFFF"},
    "2": {"url": "https://i.ibb.co/XxPBFPGy/74f8c5c8bebb711f0f92cef313ffb6d4.jpg", "price": 700, "name": "البنفسج المظلم", "color": "#FFFFFF"},
    "3": {"url": "https://i.ibb.co/ccKQVm0M/0e3fc888eadfa22b852b1437419e548e.jpg", "price": 1000, "name": "ليالي البنفسج", "color": "#FFFFFF"},
    "4": {"url": "https://i.ibb.co/PZNCzQS8/9d1247f8c186708963115d9ba0bc8977.jpg", "price": 6000, "name": "الأزرق الملكي", "color": "#00E5FF"},
    "5": {"url": "https://i.ibb.co/sJMs2NdR/e0bd76c09d1751a305830eb0fcec27d8.jpg", "price": 2000, "name": "فضاء أزرق", "color": "#FFFFFF"},
    "6": {"url": "https://i.ibb.co/JRjYbkrr/b59066e9e3a0619e8069aa6d35ba994d.jpg", "price": 10000, "name": "النخبة البنفسجية", "color": "#FFFFFF"},
    "7": {"url": "https://i.ibb.co/67krxH9W/eee9b34948a2f314cae78f8dd0e3e70a.jpg", "price": 50000, "name": "الأبيض النقي", "color": "#000000"},
    "8": {"url": "https://i.ibb.co/gLVXvKpv/ece77d283b543be1824380cacab2ac64.jpg", "price": 7000, "name": "الرخام الأسود", "color": "#FFFFFF"},
    "9": {"url": "https://i.ibb.co/Ld4xZfWh/1368816d0d44c6d4a0911262fcc69df0.jpg", "price": 16000, "name": "أحمر دموي", "color": "#FF0000"},
    "16": {"url": "https://i.ibb.co/tPFJ2FTz/01d8d2d501f37741d7702c70fafba4ef.jpg", "price": 1000000, "name": "التاج الأبيض", "color": "#000000"}
}

DEFAULT_BG = "https://i.ibb.co/4nXX8y2z/fc17d0243302d37f7759059464e4404a.jpg"
xp_cooldown = {}

# رابط خط احترافي خارجي لضمان الجودة
FONT_URL = "https://github.com/googlefonts/cairo/raw/main/fonts/ttf/Cairo-Bold.ttf"

def format_num(n):
    if n >= 1e9: return f"{n/1e9:.1f}B"
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

def get_user(uid):
    u = collection.find_one({"_id": str(uid)})
    if not u:
        u = {"_id": str(uid), "xp": 0, "level": 0, "bg": DEFAULT_BG, "t_color": "#FFFFFF"}
        collection.insert_one(u)
    return u

async def generate_card(name, level, xp, avatar_url, bg_url, text_color):
    try:
        # تحميل الخلفية
        bg_res = requests.get(bg_url, timeout=10)
        img = Image.open(BytesIO(bg_res.content)).convert("RGBA").resize((900, 300))
        
        # تحميل الأفاتار
        av_res = requests.get(avatar_url, timeout=10)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((200, 200))
        
        # تحميل الخط الاحترافي
        font_res = requests.get(FONT_URL)
        font_main = ImageFont.truetype(BytesIO(font_res.content), 50)
        font_sub = ImageFont.truetype(BytesIO(font_res.content), 40)
        
        # جعل الأفاتار دائري بدقة عالية
        mask = Image.new("L", (200, 200), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 200, 200), fill=255)
        img.paste(av, (45, 50), mask)
        
        draw = ImageDraw.Draw(img)
        
        # دالة الكتابة الاحترافية (تضيف حدود سوداء لجعل النص بارزاً جداً)
        def draw_text_with_outline(position, text, font, fill_color):
            x, y = position
            outline_color = "black" if fill_color != "black" else "white"
            # رسم الإطار (Stroke)
            for adj in range(-2, 3):
                for ops in range(-2, 3):
                    draw.text((x+adj, y+ops), text, font=font, fill=outline_color)
            # رسم النص الأساسي
            draw.text((x, y), text, font=font, fill=fill_color)

        # المواقع والنصوص بأحجام ضخمة
        draw_text_with_outline((280, 50), name, font_main, text_color)
        draw_text_with_outline((280, 135), f"LEVEL: {level}", font_sub, text_color)
        draw_text_with_outline((280, 205), f"XP: {format_num(xp)}", font_sub, text_color)
        
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Error: {e}")
        return None

class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = SkyBot()

def is_staff(it: discord.Interaction):
    return it.user.id == OWNER_ID or any(r.id in ADMIN_ROLES for r in it.user.roles)

@bot.tree.command(name="rank", description="عرض بطاقتك الصورية")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if it.channel_id != ALLOWED_RANK_CH_ID:
        return await it.response.send_message(f"❌ التوجه لـ <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
    
    await it.response.defer()
    target = member or it.user
    if target.bot: return await it.followup.send("❌ البوتات لا تملك رتباً.")
    
    u = get_user(target.id)
    card = await generate_card(target.display_name, u['level'], u['xp'], target.display_avatar.url, u.get('bg', DEFAULT_BG), u.get('t_color', '#FFFFFF'))
    
    if card:
        await it.followup.send(file=discord.File(card, f"rank_{target.id}.png"))
    else:
        await it.followup.send("❌ فشل إنشاء البطاقة، جرب مرة أخرى.")

@bot.tree.command(name="store", description="متجر الخلفيات")
async def store(it: discord.Interaction):
    emb = discord.Embed(title="🛒 متجر Sky Data الرسمي", description="تميز ببطاقة فريدة!", color=0x9b59b6)
    for k, v in STORE_BG.items():
        emb.add_field(name=f"رقم {k}", value=f"**{v['name']}**\nالسعر: `{format_num(v['price'])}` XP", inline=True)
    await it.response.send_message(embed=emb)

@bot.tree.command(name="buy", description="شراء خلفية")
async def buy(it: discord.Interaction, number: str):
    if number not in STORE_BG: return await it.response.send_message("❌ غير موجود.")
    u = get_user(it.user.id)
    item = STORE_BG[number]
    if u['xp'] < item['price']: return await it.response.send_message("❌ XP غير كافٍ.")
    
    collection.update_one({"_id": str(it.user.id)}, {"$inc": {"xp": -item['price']}, "$set": {"bg": item['url'], "t_color": item['color']}})
    await it.response.send_message(f"✅ تم الشراء! افحص `/rank`.")

@bot.tree.command(name="top", description="المتصدرين")
async def top(it: discord.Interaction):
    await it.response.defer()
    potential_tops = list(collection.find().sort("xp", -1).limit(40))
    emb = discord.Embed(title="🏆 أساطير Sky Data (بشر فقط)", color=0xf1c40f)
    desc = ""
    count = 0
    for u in potential_tops:
        if count >= 10: break
        member = it.guild.get_member(int(u["_id"]))
        if member and not member.bot:
            count += 1
            desc += f"**#{count}** | {member.mention} - لفل `{u['level']}` - `{format_num(u['xp'])}` XP\n"
    emb.description = desc
    await it.followup.send(embed=emb)

@bot.tree.command(name="give_xp", description="إضافة XP (إداري)")
async def give_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌ للإدارة فقط.")
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": amount}}, upsert=True)
    await it.response.send_message(f"✅ أضيفت `{amount}` لـ {member.mention}.")

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
        if ch: await ch.send(f"🎊 {msg.author.mention} لفل **{new_lvl}**!")
        if new_lvl in LEVEL_ROLES:
            role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
            if role: await msg.author.add_roles(role)
    await bot.process_commands(msg)

app = Flask('')
@app.route('/')
def home(): return "Active"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
