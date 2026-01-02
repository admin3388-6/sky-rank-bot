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

# --- 1. الإعدادات والربط ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"]
collection = db["rank_system"]
track_col = db["rank_tracking"]

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

RANK_IMAGES = {
    50: "https://i.ibb.co/57wV2SH/lv50.webp",
    40: "https://i.ibb.co/ds0DXYjv/lv40.webp",
    30: "https://i.ibb.co/Ng1Zygy1/lv30.webp",
    20: "https://i.ibb.co/cK5Z3ZgC/lv20.webp",
    10: "https://i.ibb.co/0Rb0R6cw/lv10.webp",
    5: "https://i.ibb.co/fV7n1685/lv5.webp"
}

ICONS = {
    "level": "https://i.ibb.co/cBwBDbd/lvlicon-193x70p.png",
    "name": "https://i.ibb.co/kgQGjj36/nameicon-193x70.png",
    "xp": "https://i.ibb.co/whbnGb0H/xpicon-110x59p.png"
}

# المتجر الكامل كما طلبته
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

DEFAULT_BG = STORE_BG["1"]["url"]
xp_cooldown = {}

# --- 2. محرك الرسم المطور (لحل مشكلة الخط الصغير) ---
def format_num(n):
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.1f}K"
    return str(int(n))

async def fetch_img(url):
    res = requests.get(url, timeout=10)
    return Image.open(BytesIO(res.content)).convert("RGBA")

def get_rank_badge(lvl):
    for threshold in sorted(RANK_IMAGES.keys(), reverse=True):
        if lvl >= threshold: return RANK_IMAGES[threshold]
    return RANK_IMAGES[5]

# دالة لتحميل خط كبير
def load_font(size):
    try:
        # يحاول تحميل خط موجود في السيرفرات عادة
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except:
            return ImageFont.load_default() # الخيار الأخير (صغير)

async def generate_card(user_data, member):
    try:
        base = (await fetch_img(user_data.get('bg', DEFAULT_BG))).resize((950, 350))
        
        # الأيقونات (تم تكبيرها لتسع النص)
        name_bar = (await fetch_img(ICONS["name"])).resize((330, 95))
        lvl_bar = (await fetch_img(ICONS["level"])).resize((330, 95))
        xp_bar = (await fetch_img(ICONS["xp"])).resize((240, 85))
        
        # الأفاتار
        av_res = requests.get(member.display_avatar.url)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((220, 220))
        mask = Image.new("L", (220, 220), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 220, 220), fill=255)
        
        base.paste(av, (50, 65), mask)
        base.paste(name_bar, (310, 45), name_bar)
        base.paste(lvl_bar, (310, 145), lvl_bar)
        base.paste(xp_bar, (310, 245), xp_bar)
        
        # شارة الرتبة
        rank_badge = (await fetch_img(get_rank_badge(user_data['level']))).resize((140, 140))
        base.paste(rank_badge, (780, 45), rank_badge)

        draw = ImageDraw.Draw(base)
        t_color = user_data.get('t_color', 'white')
        
        # تحميل خطوط بأحجام كبيرة
        font_large = load_font(45) # للأرقام
        font_med = load_font(35)   # للاسم
        
        # رسم النصوص (الإحداثيات معدلة لعدم التداخل)
        # الاسم
        draw.text((430, 75), f"{member.display_name[:12]}", fill=t_color, font=font_med, stroke_width=2, stroke_fill="black")
        # المستوى (رقم كبير)
        draw.text((430, 175), f"{user_data['level']}", fill=t_color, font=font_large, stroke_width=3, stroke_fill="black")
        # النقاط
        draw.text((410, 270), f"{format_num(user_data['xp'])}", fill=t_color, font=font_med, stroke_width=2, stroke_fill="black")

        buf = BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Drawing Error: {e}")
        return None

# --- 3. البوت ---
class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self): await self.tree.sync()

bot = SkyBot()

def is_staff(it: discord.Interaction):
    return it.user.id == OWNER_ID or any(r.id in ADMIN_ROLES for r in it.user.roles)

async def check_channel(it: discord.Interaction):
    if it.channel_id != ALLOWED_RANK_CH_ID:
        await it.response.send_message(f"❌ <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
        return False
    return True

# --- 4. أوامر الإدارة الناقصة (Set, Remove, Reset) ---

@bot.tree.command(name="set_xp", description="تحديد نقاط عضو (إدارة)")
async def set_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌", ephemeral=True)
    lvl = min(amount // 1000, 50)
    collection.update_one({"_id": str(member.id)}, {"$set": {"xp": amount, "level": lvl}}, upsert=True)
    await it.response.send_message(f"✅ تم تحديد نقاط {member.mention} بـ {amount} (مستوى {lvl}).")

@bot.tree.command(name="remove_xp", description="خصم نقاط من عضو (إدارة)")
async def remove_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌", ephemeral=True)
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": -amount}}, upsert=True)
    await it.response.send_message(f"✅ تم خصم {amount} نقطة من {member.mention}.")

@bot.tree.command(name="reset_all", description="تصفير نقاط السيرفر بالكامل (Owner Only)")
async def reset_all(it: discord.Interaction):
    if it.user.id != OWNER_ID: return await it.response.send_message("❌ هذا الأمر للمالك فقط!", ephemeral=True)
    collection.update_many({}, {"$set": {"xp": 0, "level": 0}})
    track_col.delete_many({}) # تصفير الترتيب أيضاً
    await it.response.send_message("⚠️ تم تصفير جميع النقاط والمستويات والترتيب في السيرفر!")

@bot.tree.command(name="give_xp", description="إعطاء نقاط (إدارة)")
async def give_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌", ephemeral=True)
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": amount}}, upsert=True)
    await it.response.send_message(f"✅ تم إضافة {amount} نقطة لـ {member.mention}.")

# --- 5. أوامر المتجر والرانك ---

@bot.tree.command(name="rank", description="عرض البطاقة")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if not await check_channel(it): return
    await it.response.defer()
    target = member or it.user
    u = collection.find_one({"_id": str(target.id)}) or {"_id": str(target.id), "xp": 0, "level": 0}
    card = await generate_card(u, target)
    if card: await it.followup.send(file=discord.File(card, "rank.png"))
    else: await it.followup.send("❌ خطأ في الرسم.")

@bot.tree.command(name="store", description="عرض المتجر بالصور")
async def store(it: discord.Interaction):
    if not await check_channel(it): return
    
    # هنا التعديل: إرسال قائمة من Embeds تحتوي الصور
    embeds = []
    # سنعرض أول 10 فقط لأن ديسكورد يمنع أكثر من 10 في رسالة واحدة
    items = list(STORE_BG.items())[:10]
    
    for k, v in items:
        emb = discord.Embed(title=f"#{k} | {v['name']}", description=f"💰 السعر: `{format_num(v['price'])}` XP", color=0x9b59b6)
        emb.set_image(url=v['url']) # الصورة تظهر مباشرة
        embeds.append(emb)
    
    await it.response.send_message("🛍️ **متجر الخلفيات** (استخدم `/buy رقم` للشراء):", embeds=embeds)

@bot.tree.command(name="buy", description="شراء خلفية")
async def buy(it: discord.Interaction, number: str):
    if not await check_channel(it): return
    if number not in STORE_BG: return await it.response.send_message("❌ رقم غير صحيح.", ephemeral=True)
    
    u = collection.find_one({"_id": str(it.user.id)}) or {"_id": str(it.user.id), "xp": 0}
    item = STORE_BG[number]
    
    if u.get('xp', 0) < item['price']: return await it.response.send_message("❌ نقاطك غير كافية!", ephemeral=True)
    
    collection.update_one({"_id": str(it.user.id)}, {"$inc": {"xp": -item['price']}, "$set": {"bg": item['url'], "t_color": item['color']}})
    await it.response.send_message(f"✅ تم شراء **{item['name']}** بنجاح!")

@bot.tree.command(name="top", description="التوب")
async def top(it: discord.Interaction):
    if not await check_channel(it): return
    await it.response.defer()
    
    all_users = list(collection.find().sort("xp", -1).limit(10))
    desc = ""
    for i, u in enumerate(all_users):
        m = it.guild.get_member(int(u["_id"]))
        if m:
            # الأسهم
            old_rank = track_col.find_one({"_id": u["_id"]})
            trend = "⏺️"
            curr_pos = i + 1
            if old_rank:
                if curr_pos < old_rank['pos']: trend = "⬆️"
                elif curr_pos > old_rank['pos']: trend = "⬇️"
            track_col.update_one({"_id": u["_id"]}, {"$set": {"pos": curr_pos}}, upsert=True)
            
            desc += f"{trend} **#{curr_pos}** | {m.mention} | 🌟 {u['level']} | ✨ {format_num(u['xp'])}\n"
            
    emb = discord.Embed(title="🏆 قائمة المتصدرين", description=desc or "لا يوجد بيانات", color=0xf1c40f)
    await it.followup.send(embed=emb)

# --- 6. الرسائل ---
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = str(msg.author.id)
    now = datetime.now()
    
    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=20): return
    xp_cooldown[uid] = now
    
    u = collection.find_one({"_id": uid}) or {"_id": uid, "xp": 0, "level": 0, "msg_count": 0, "start_time": time.time()}
    new_xp = u['xp'] + random.randint(15, 25)
    new_lvl = min(new_xp // 1000, 50)
    
    collection.update_one({"_id": uid}, {"$set": {"xp": new_xp, "level": new_lvl}, "$inc": {"msg_count": 1}}, upsert=True)
    
    if new_lvl > u['level']:
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch:
            time_diff = (time.time() - u.get('start_time', time.time())) / 60
            eff = min(100, int((u.get('msg_count', 1) / (time_diff + 1)) * 10))
            
            emb = discord.Embed(description=f"🎉 {msg.author.mention} وصل للمستوى **{new_lvl}**! (تفاعل: {eff}%)", color=0x00ff00)
            emb.set_thumbnail(url=get_rank_badge(new_lvl))
            await ch.send(embed=emb)
            
            if new_lvl in LEVEL_ROLES:
                role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
                if role: 
                    try: await msg.author.add_roles(role)
                    except: pass
            
            collection.update_one({"_id": uid}, {"$set": {"msg_count": 0, "start_time": time.time()}})

    await bot.process_commands(msg)

# --- 7. التشغيل ---
app = Flask('')
@app.route('/')
def home(): return "Ready"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
