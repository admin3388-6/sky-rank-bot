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

DEFAULT_BG_ID = "1"
xp_cooldown = {}

# --- 2. محرك الرسم المطور (Text Only + Ring) ---
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

# تحميل خط افتراضي كبير
def load_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()

async def generate_card(user_data, member):
    try:
        # تحديد الخلفية
        bg_id = user_data.get('bg_id', DEFAULT_BG_ID)
        if bg_id not in STORE_BG: bg_id = DEFAULT_BG_ID
        bg_info = STORE_BG[bg_id]
        
        # تحميل الخلفية وتغيير الحجم
        base = (await fetch_img(bg_info['url'])).resize((950, 350))
        draw = ImageDraw.Draw(base)

        # 1. الأفاتار مع الحلقة الملونة
        av_size = 220
        av_pos = (50, 65)
        av_res = requests.get(member.display_avatar.url)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((av_size, av_size))
        
        # إنشاء القناع الدائري للأفاتار
        mask = Image.new("L", (av_size, av_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, av_size, av_size), fill=255)
        
        # رسم الحلقة الملونة (Ring)
        ring_color = bg_info['color']
        ring_thickness = 8
        # نرسم دائرة أكبر قليلاً خلف الأفاتار لتكون هي الإطار
        draw.ellipse(
            (av_pos[0] - ring_thickness, av_pos[1] - ring_thickness, 
             av_pos[0] + av_size + ring_thickness, av_pos[1] + av_size + ring_thickness),
            fill=ring_color
        )
        # لصق الأفاتار فوق الحلقة
        base.paste(av, av_pos, mask)

        # 2. النصوص (بدون صور خلفية)
        t_color = bg_info['color'] # لون النص نفس لون البانر المميز
        font_large = load_font(60) # للأرقام
        font_med = load_font(40)   # للاسم
        
        # الاسم
        draw.text((320, 60), f"{member.display_name[:15]}", fill="white", font=font_med, stroke_width=2, stroke_fill="black")
        
        # Level Text
        draw.text((320, 140), "LEVEL:", fill="white", font=load_font(30), stroke_width=1, stroke_fill="black")
        draw.text((440, 130), f"{user_data['level']}", fill=t_color, font=font_large, stroke_width=3, stroke_fill="black")
        
        # XP Text
        draw.text((320, 240), "XP:", fill="white", font=load_font(30), stroke_width=1, stroke_fill="black")
        draw.text((440, 230), f"{format_num(user_data['xp'])}", fill=t_color, font=font_large, stroke_width=3, stroke_fill="black")

        # 3. شارة الرتبة (التاج)
        rank_badge = (await fetch_img(get_rank_badge(user_data['level']))).resize((150, 150))
        base.paste(rank_badge, (750, 100), rank_badge)

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

# --- 4. أوامر الإدارة ---

@bot.tree.command(name="set_xp", description="تحديد نقاط عضو (إدارة)")
async def set_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌", ephemeral=True)
    if member.bot: return await it.response.send_message("🤖 البوتات لا تملك نقاطاً.", ephemeral=True)
    
    lvl = min(amount // 1000, 50)
    collection.update_one({"_id": str(member.id)}, {"$set": {"xp": amount, "level": lvl}}, upsert=True)
    await it.response.send_message(f"✅ تم تحديد نقاط {member.mention} بـ {amount} (مستوى {lvl}).")

@bot.tree.command(name="remove_xp", description="خصم نقاط من عضو (إدارة)")
async def remove_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌", ephemeral=True)
    if member.bot: return await it.response.send_message("🤖", ephemeral=True)
    
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": -amount}}, upsert=True)
    await it.response.send_message(f"✅ تم خصم {amount} نقطة من {member.mention}.")

@bot.tree.command(name="reset_all", description="تصفير كامل (Owner Only)")
async def reset_all(it: discord.Interaction):
    if it.user.id != OWNER_ID: return await it.response.send_message("❌ للمالك فقط!", ephemeral=True)
    collection.delete_many({}) # حذف كل البيانات
    track_col.delete_many({})  # حذف الترتيب
    await it.response.send_message("⚠️ تم تصفير السيرفر بالكامل!")

# --- 5. أوامر المتجر الذكي والرانك ---

@bot.tree.command(name="rank", description="عرض البطاقة")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if not await check_channel(it): return
    await it.response.defer()
    target = member or it.user
    
    if target.bot:
        return await it.followup.send("🤖 البوتات ليس لديها بطاقة رانك.")

    # جلب البيانات أو إنشاء جديد
    u = collection.find_one({"_id": str(target.id)}) 
    if not u:
        u = {"_id": str(target.id), "xp": 0, "level": 0, "bg_id": "1", "inventory": ["1"]}
        collection.insert_one(u)
    
    # التأكد من وجود الحقول الجديدة
    if "inventory" not in u:
        collection.update_one({"_id": str(target.id)}, {"$set": {"inventory": ["1"], "bg_id": "1"}})
        u["inventory"] = ["1"]
        u["bg_id"] = "1"

    card = await generate_card(u, target)
    if card: await it.followup.send(file=discord.File(card, "rank.png"))
    else: await it.followup.send("❌ خطأ تقني.")

@bot.tree.command(name="store", description="المتجر الذكي: شاهد ما تملك واشترِ الجديد")
async def store(it: discord.Interaction):
    if not await check_channel(it): return
    
    # جلب مخزون المستخدم لمعرفة ماذا يملك
    u = collection.find_one({"_id": str(it.user.id)}) or {"inventory": ["1"]}
    user_inv = u.get("inventory", ["1"])
    
    embeds = []
    items = list(STORE_BG.items())[:10]
    
    for k, v in items:
        # حالة العنصر
        status = "✅ مملوك (استخدم الأمر للتجهيز)" if k in user_inv else f"💰 السعر: `{format_num(v['price'])}` XP"
        color = 0x00ff00 if k in user_inv else 0x9b59b6
        
        emb = discord.Embed(title=f"#{k} | {v['name']}", description=f"**الحالة:** {status}", color=color)
        emb.set_image(url=v['url'])
        emb.set_footer(text=f"للشراء أو التجهيز: /buy {k}")
        embeds.append(emb)
    
    await it.response.send_message("🛍️ **متجر الخلفيات**", embeds=embeds)

@bot.tree.command(name="buy", description="شراء أو تجهيز خلفية (نظام ذكي)")
async def buy(it: discord.Interaction, number: str):
    if not await check_channel(it): return
    if number not in STORE_BG: return await it.response.send_message("❌ رقم غير صحيح.", ephemeral=True)
    
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid})
    if not u:
        u = {"_id": uid, "xp": 0, "inventory": ["1"], "bg_id": "1"}
        collection.insert_one(u)

    inv = u.get("inventory", ["1"])
    item = STORE_BG[number]

    # 1. سيناريو التجهيز (يملك الخلفية مسبقاً)
    if number in inv:
        if u.get("bg_id") == number:
            return await it.response.send_message(f"⚠️ بانر **{item['name']}** مجهز بالفعل!", ephemeral=True)
        
        collection.update_one({"_id": uid}, {"$set": {"bg_id": number}})
        return await it.response.send_message(f"✅ **تم التجهيز!** خلفيتك الآن هي: {item['name']}.")

    # 2. سيناريو الشراء (لا يملكها)
    if u.get('xp', 0) < item['price']:
        return await it.response.send_message(f"❌ نقاطك غير كافية! تحتاج `{format_num(item['price'])}` XP.", ephemeral=True)
    
    # خصم النقاط + إضافة للمخزون + تجهيز
    collection.update_one({"_id": uid}, {
        "$inc": {"xp": -item['price']},
        "$push": {"inventory": number},
        "$set": {"bg_id": number}
    })
    
    await it.response.send_message(f"🎉 **مبروك!** تم شراء وتجهيز **{item['name']}** بنجاح.")

@bot.tree.command(name="top", description="المتصدرين (أخضر/أحمر/أصفر)")
async def top(it: discord.Interaction):
    if not await check_channel(it): return
    await it.response.defer()
    
    # استثناء البوتات من التوب وعدم جلبهم
    # ملاحظة: نقوم بجلب الأعضاء وتصفيتهم
    all_users = collection.find().sort("xp", -1)
    
    desc = ""
    rank_count = 0
    
    for u in all_users:
        if rank_count >= 10: break
        
        member = it.guild.get_member(int(u["_id"]))
        if not member or member.bot: continue # تجاهل البوتات ومن خرجوا
        
        rank_count += 1
        
        # منطق الأسهم (Progress)
        old_data = track_col.find_one({"_id": u["_id"]})
        trend = "🟡" # افتراضي (أصفر - ركود)
        
        if old_data:
            old_pos = old_data['pos']
            if rank_count < old_pos: trend = "🟢" # صعد (رقم أقل يعني مركز أفضل)
            elif rank_count > old_pos: trend = "🔴" # نزل
        
        # تحديث الترتيب الحالي للمرة القادمة
        track_col.update_one({"_id": u["_id"]}, {"$set": {"pos": rank_count}}, upsert=True)
        
        desc += f"{trend} **#{rank_count}** | {member.mention} \n╚ 👑 Lvl {u['level']} | ✨ {format_num(u['xp'])} XP\n\n"
            
    emb = discord.Embed(title="🏆 قائمة الأساطير (Top 10)", description=desc or "لا يوجد بيانات", color=0xf1c40f)
    await it.followup.send(embed=emb)

# --- 6. الرسائل والترقية ---
@bot.event
async def on_message(msg):
    # منع البوتات نهائياً
    if msg.author.bot or not msg.guild: return
    
    uid = str(msg.author.id)
    now = datetime.now()
    
    # نظام الحماية من السبام
    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=20): return
    xp_cooldown[uid] = now
    
    # جلب البيانات
    u = collection.find_one({"_id": uid})
    if not u:
        u = {"_id": uid, "xp": 0, "level": 0, "msg_count": 0, "start_time": time.time(), "inventory": ["1"], "bg_id": "1"}
        collection.insert_one(u)
    
    new_xp = u['xp'] + random.randint(15, 25)
    new_lvl = min(new_xp // 1000, 50)
    
    collection.update_one({"_id": uid}, {"$set": {"xp": new_xp, "level": new_lvl}, "$inc": {"msg_count": 1}})
    
    # الترقية
    if new_lvl > u['level']:
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch:
            # حساب الكفاءة (كمثال على التحسينات)
            time_diff = (time.time() - u.get('start_time', time.time())) / 60
            eff = min(100, int((u.get('msg_count', 1) / (time_diff + 1)) * 10))
            
            emb = discord.Embed(title="🚀 LEVEL UP!", description=f"مبروك {msg.author.mention}!", color=0x00ff00)
            emb.add_field(name="المستوى الحالي", value=f"**{new_lvl}**", inline=True)
            emb.add_field(name="كفاءة التفاعل", value=f"`{eff}%` 🔥", inline=True)
            emb.set_thumbnail(url=msg.author.display_avatar.url)
            emb.set_image(url=RANK_IMAGES.get(new_lvl, RANK_IMAGES[5])) # صورة الرتبة كصورة كبيرة
            
            await ch.send(f"{msg.author.mention}", embed=emb)
            
            # إعطاء الرتبة
            if new_lvl in LEVEL_ROLES:
                role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
                if role: 
                    try: await msg.author.add_roles(role)
                    except: pass
            
            # تصفير عداد الكفاءة للفل القادم
            collection.update_one({"_id": uid}, {"$set": {"msg_count": 0, "start_time": time.time()}})

    await bot.process_commands(msg)

# --- 7. التشغيل ---
app = Flask('')
@app.route('/')
def home(): return "Sky System V4 Active"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
