import discord
from discord.ext import commands
from discord import app_commands
import os, random, asyncio, requests, time
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta

# --- 1. الإعدادات الأساسية ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"]
collection = db["rank_system"]
track_col = db["rank_tracking"]

# إعدادات القنوات والرتب
UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213
OWNER_ID = 1429183440485486679 
ADMIN_ROLES = [1448639184532144128, 1448638848098631881, 1448638848090509381]

LEVEL_ROLES = {
    10: 1448821273756172348, 20: 1448821177605947402,
    30: 1448821103391674398, 40: 1448821022462709891, 50: 1448820918490239027
}

RANK_IMAGES = {
    50: "https://i.ibb.co/57wV2SH/lv50.webp",
    40: "https://i.ibb.co/ds0DXYjv/lv40.webp",
    30: "https://i.ibb.co/Ng1Zygy1/lv30.webp",
    20: "https://i.ibb.co/cK5Z3ZgC/lv20.webp",
    10: "https://i.ibb.co/0Rb0R6cw/lv10.webp",
    5: "https://i.ibb.co/fV7n1685/lv5.webp"
}

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

DEFAULT_BG_ID = "1"
xp_cooldown = {}

# --- 2. محرك الرسم المطور (حل مشكلة الخط والنصوص) ---
def format_num(n):
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

async def fetch_img(url):
    res = requests.get(url, timeout=5)
    return Image.open(BytesIO(res.content)).convert("RGBA")

def get_font(size):
    # محاولة تحميل خط نظام أو افتراضي لضمان عدم تعليق البوت
    try:
        # إذا كنت على ريبليت أو لينكس، غالباً يتوفر خط DejaVu
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        try: return ImageFont.truetype("arial.ttf", size)
        except: return ImageFont.load_default()

async def generate_card(user_data, member):
    try:
        bg_id = user_data.get('bg_id', DEFAULT_BG_ID)
        bg_info = STORE_BG.get(bg_id, STORE_BG[DEFAULT_BG_ID])
        
        # 1. إنشاء الخلفية
        base = (await fetch_img(bg_info['url'])).resize((950, 350))
        draw = ImageDraw.Draw(base)

        # 2. الأفاتار مع الحلقة الملونة
        av_size = 220
        av_pos = (50, 65)
        av_res = requests.get(member.display_avatar.url, timeout=5)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((av_size, av_size))
        mask = Image.new("L", (av_size, av_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, av_size, av_size), fill=255)
        
        # رسم الحلقة
        ring_color = bg_info['color']
        draw.ellipse((av_pos[0]-10, av_pos[1]-10, av_pos[0]+av_size+10, av_pos[1]+av_size+10), fill=ring_color)
        base.paste(av, av_pos, mask)

        # 3. النصوص (أحجام ضخمة وواضحة)
        t_color = bg_info['color']
        f_huge = get_font(80) 
        f_name = get_font(55)
        f_sub = get_font(35)

        # الاسم
        draw.text((320, 45), f"{member.display_name[:14]}", fill="white", font=f_name, stroke_width=3, stroke_fill="black")
        
        # Level
        draw.text((320, 135), "LEVEL", fill="white", font=f_sub, stroke_width=2, stroke_fill="black")
        draw.text((320, 180), f"{user_data['level']}", fill=t_color, font=f_huge, stroke_width=4, stroke_fill="black")
        
        # XP
        draw.text((580, 135), "XP POINTS", fill="white", font=f_sub, stroke_width=2, stroke_fill="black")
        draw.text((580, 180), f"{format_num(user_data['xp'])}", fill=t_color, font=f_huge, stroke_width=4, stroke_fill="black")

        # 4. الشارة
        rank_badge = (await fetch_img(RANK_IMAGES.get(user_data['level'] if user_data['level'] in RANK_IMAGES else 5, RANK_IMAGES[5]))).resize((170, 170))
        base.paste(rank_badge, (760, 90), rank_badge)

        buf = BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Error drawing card: {e}")
        return None

# --- 3. إعدادات البوت والأوامر ---
class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): await self.tree.sync()

bot = SkyBot()

def is_staff(it: discord.Interaction):
    return it.user.id == OWNER_ID or any(r.id in ADMIN_ROLES for r in it.user.roles)

async def check_channel(it: discord.Interaction):
    if it.channel_id != ALLOWED_RANK_CH_ID:
        await it.response.send_message(f"❌ هذا الأمر مسموح فقط في <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
        return False
    return True

# --- 4. أوامر الرانك والمخزون والتجهيز ---

@bot.tree.command(name="rank", description="عرض بطاقة المستوى الخاصة بك")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if not await check_channel(it): return
    await it.response.defer() # يمنع تعليق البوت أثناء المعالجة
    
    target = member or it.user
    if target.bot: return await it.followup.send("🤖 البوتات لا تملك مستويات.")
    
    u = collection.find_one({"_id": str(target.id)})
    if not u:
        u = {"_id": str(target.id), "xp": 0, "level": 0, "bg_id": "1", "inventory": ["1"]}
        collection.insert_one(u)

    card = await generate_card(u, target)
    if card:
        await it.followup.send(file=discord.File(card, "rank.png"))
    else:
        await it.followup.send("❌ حدث خطأ أثناء إنشاء البطاقة.")

@bot.tree.command(name="inventory", description="حقيبتك: شاهد ما تملك وقم بتجهيزه")
async def inventory(it: discord.Interaction):
    if not await check_channel(it): return
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid}) or {"inventory": ["1"], "bg_id": "1"}
    
    inv = u.get("inventory", ["1"])
    current = u.get("bg_id", "1")
    
    msg = "🎒 **خلفياتك المملوكة:**\n\n"
    for item_id in inv:
        name = STORE_BG.get(item_id, {}).get('name', '؟؟')
        status = "🟢 (مجهز حالياً)" if item_id == current else "🔴 (غير مجهز)"
        msg += f"**#{item_id}** | {name} - {status}\n"
    
    msg += "\n💡 لتجهيز خلفية اكتب: `/equip [رقم_الخلفية]`"
    await it.response.send_message(msg)

@bot.tree.command(name="equip", description="تجهيز خلفية من حقيبتك")
async def equip(it: discord.Interaction, id: str):
    if not await check_channel(it): return
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid}) or {"inventory": ["1"]}
    
    if id not in u.get("inventory", ["1"]):
        return await it.response.send_message("❌ أنت لا تملك هذه الخلفية في حقيبتك!", ephemeral=True)
    
    collection.update_one({"_id": uid}, {"$set": {"bg_id": id}})
    await it.response.send_message(f"✅ تم تجهيز الخلفية رقم **#{id}** بنجاح!")

# --- 5. نظام المتجر والبيع الذكي ---

@bot.tree.command(name="store", description="متجر البانرات")
async def store(it: discord.Interaction):
    if not await check_channel(it): return
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid}) or {"inventory": ["1"], "bg_id": "1"}
    inv = u.get("inventory", ["1"])
    
    embeds = []
    for k, v in list(STORE_BG.items())[:10]:
        status = "✅ مملوك" if k in inv else f"💰 السعر: {format_num(v['price'])} XP"
        color = 0x2ecc71 if k in inv else 0xe91e63
        
        emb = discord.Embed(title=f"بانر #{k} - {v['name']}", description=f"الحالة: **{status}**", color=color)
        emb.set_image(url=v['url'])
        embeds.append(emb)
    
    await it.response.send_message("🛒 **متجر السيرفر الذكي**", embeds=embeds)

@bot.tree.command(name="buy", description="شراء بانر جديد")
async def buy(it: discord.Interaction, id: str):
    if not await check_channel(it): return
    if id not in STORE_BG: return await it.response.send_message("❌ هذا الرقم غير موجود بالمتجر.")
    
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid}) or {"xp": 0, "inventory": ["1"]}
    
    if id in u.get("inventory", ["1"]):
        return await it.response.send_message("⚠️ أنت تملك هذا البانر بالفعل! استخدم `/equip` لتجهيزه.", ephemeral=True)
    
    price = STORE_BG[id]['price']
    if u.get('xp', 0) < price:
        return await it.response.send_message(f"❌ نقاطك غير كافية! تحتاج {format_num(price)} XP.")
    
    collection.update_one({"_id": uid}, {
        "$inc": {"xp": -price},
        "$push": {"inventory": id},
        "$set": {"bg_id": id}
    })
    await it.response.send_message(f"🎉 مبروك! تم شراء وتجهيز بانر **{STORE_BG[id]['name']}** بنجاح.")

# --- 6. قائمة المتصدرين الملونة (Trend System) ---

@bot.tree.command(name="top", description="قائمة المتصدرين بالسيرفر")
async def top(it: discord.Interaction):
    if not await check_channel(it): return
    await it.response.defer()
    
    all_users = list(collection.find().sort("xp", -1))
    desc = ""
    rank_count = 0
    
    for u in all_users:
        member = it.guild.get_member(int(u["_id"]))
        if not member or member.bot: continue
        
        rank_count += 1
        if rank_count > 10: break
        
        # نظام تتبع المركز (Trend)
        old = track_col.find_one({"_id": u["_id"]})
        trend = "🟡" # لا تغيير
        if old:
            if rank_count < old['pos']: trend = "🟢" # صعد
            elif rank_count > old['pos']: trend = "🔴" # نزل
        
        track_col.update_one({"_id": u["_id"]}, {"$set": {"pos": rank_count}}, upsert=True)
        desc += f"{trend} **#{rank_count}** | {member.mention}\n╚ المستوي: `{u['level']}` | النقاط: `{format_num(u['xp'])}`\n\n"

    emb = discord.Embed(title="🏆 قائمة الأساطير", description=desc or "لا يوجد بيانات بعد.", color=0xf1c40f)
    await it.followup.send(embed=emb)

# --- 7. نظام التفاعل والترقية ومنع البوتات ---

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return # منع البوتات تماماً
    
    uid = str(msg.author.id)
    now = datetime.now()
    
    # منع Spam النقاط (كل 20 ثانية)
    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=20): return
    xp_cooldown[uid] = now
    
    u = collection.find_one({"_id": uid})
    if not u:
        u = {"_id": uid, "xp": 0, "level": 0, "bg_id": "1", "inventory": ["1"]}
        collection.insert_one(u)
        
    xp_add = random.randint(15, 25)
    new_xp = u['xp'] + xp_add
    new_lvl = new_xp // 1000
    
    collection.update_one({"_id": uid}, {"$set": {"xp": new_xp, "level": new_lvl}})
    
    # رسالة الترقية
    if new_lvl > u.get('level', 0):
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch:
            emb = discord.Embed(title="🎊 مستوى جديد!", description=f"كفو {msg.author.mention}! وصلت للمستوى **{new_lvl}**", color=0x2ecc71)
            emb.set_thumbnail(url=msg.author.display_avatar.url)
            await ch.send(embed=emb)
            
            # إضافة الرتبة تلقائياً
            if new_lvl in LEVEL_ROLES:
                role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
                if role: await msg.author.add_roles(role)

    await bot.process_commands(msg)

# --- 8. تشغيل البوت ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
