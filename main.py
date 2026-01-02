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

# --- 2. محرك الرسم المطور (حل مشكلة الخط نهائياً) ---
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

# دالة ذكية لتحميل خط خارجي (هنا السر في تكبير الخط)
def get_font(size):
    font_path = "roboto_bold.ttf"
    if not os.path.exists(font_path):
        try:
            # تحميل الخط من رابط مباشر إذا لم يكن موجوداً
            url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
            r = requests.get(url)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except:
            return ImageFont.load_default()
    
    return ImageFont.truetype(font_path, size)

async def generate_card(user_data, member):
    try:
        # البيانات
        bg_id = user_data.get('bg_id', DEFAULT_BG_ID)
        if bg_id not in STORE_BG: bg_id = DEFAULT_BG_ID
        bg_info = STORE_BG[bg_id]
        
        # الخلفية
        base = (await fetch_img(bg_info['url'])).resize((950, 350))
        draw = ImageDraw.Draw(base)

        # 1. الأفاتار مع الحلقة
        av_size = 220
        av_pos = (50, 65)
        av_res = requests.get(member.display_avatar.url)
        av = Image.open(BytesIO(av_res.content)).convert("RGBA").resize((av_size, av_size))
        
        mask = Image.new("L", (av_size, av_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, av_size, av_size), fill=255)
        
        # الحلقة الملونة
        ring_color = bg_info['color']
        draw.ellipse((av_pos[0]-8, av_pos[1]-8, av_pos[0]+av_size+8, av_pos[1]+av_size+8), fill=ring_color)
        base.paste(av, av_pos, mask)

        # 2. النصوص (بحجم ضخم جداً الآن)
        t_color = bg_info['color']
        
        # تحميل الخطوط بالأحجام الكبيرة
        font_huge = get_font(75) # للأرقام (ضخم)
        font_name = get_font(45) # للاسم
        font_label = get_font(30) # لكلمة Level/XP

        # الاسم
        draw.text((320, 50), f"{member.display_name[:14]}", fill="white", font=font_name, stroke_width=2, stroke_fill="black")
        
        # Level
        draw.text((320, 140), "LEVEL", fill="white", font=font_label, stroke_width=1, stroke_fill="black")
        draw.text((320, 170), f"{user_data['level']}", fill=t_color, font=font_huge, stroke_width=4, stroke_fill="black")
        
        # XP
        draw.text((550, 140), "XP POINTS", fill="white", font=font_label, stroke_width=1, stroke_fill="black")
        draw.text((550, 170), f"{format_num(user_data['xp'])}", fill=t_color, font=font_huge, stroke_width=4, stroke_fill="black")

        # 3. شارة الرتبة
        rank_badge = (await fetch_img(get_rank_badge(user_data['level']))).resize((160, 160))
        base.paste(rank_badge, (760, 95), rank_badge)

        buf = BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Error: {e}"); return None

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
@bot.tree.command(name="set_xp", description="تعديل نقاط (إدارة)")
async def set_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌", ephemeral=True)
    if member.bot: return await it.response.send_message("🤖", ephemeral=True)
    collection.update_one({"_id": str(member.id)}, {"$set": {"xp": amount, "level": amount // 1000}}, upsert=True)
    await it.response.send_message(f"✅ تم.")

@bot.tree.command(name="remove_xp", description="خصم نقاط (إدارة)")
async def remove_xp(it: discord.Interaction, member: discord.Member, amount: int):
    if not is_staff(it): return await it.response.send_message("❌", ephemeral=True)
    collection.update_one({"_id": str(member.id)}, {"$inc": {"xp": -amount}}, upsert=True)
    await it.response.send_message(f"✅ تم.")

@bot.tree.command(name="reset_all", description="تصفير شامل (Owner)")
async def reset_all(it: discord.Interaction):
    if it.user.id != OWNER_ID: return await it.response.send_message("❌", ephemeral=True)
    collection.delete_many({})
    track_col.delete_many({})
    await it.response.send_message("⚠️ تم تصفير السيرفر.")

# --- 5. نظام المتجر، الحقيبة، والتجهيز ---

@bot.tree.command(name="rank", description="عرض البطاقة")
async def rank(it: discord.Interaction, member: discord.Member = None):
    if not await check_channel(it): return
    await it.response.defer()
    target = member or it.user
    if target.bot: return await it.followup.send("🤖")
    
    u = collection.find_one({"_id": str(target.id)})
    if not u:
        collection.insert_one({"_id": str(target.id), "xp": 0, "level": 0, "bg_id": "1", "inventory": ["1"]})
        u = collection.find_one({"_id": str(target.id)})

    card = await generate_card(u, target)
    if card: await it.followup.send(file=discord.File(card, "rank.png"))

@bot.tree.command(name="inventory", description="عرض ممتلكاتك وتجهيزها")
async def inventory(it: discord.Interaction):
    if not await check_channel(it): return
    
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid}) or {"inventory": ["1"], "bg_id": "1"}
    inv = u.get("inventory", ["1"])
    current_bg = u.get("bg_id", "1")
    
    desc = ""
    for item_id in inv:
        if item_id in STORE_BG:
            item = STORE_BG[item_id]
            status = "💠 **مجهز حالياً**" if item_id == current_bg else ""
            desc += f"**[{item_id}] {item['name']}** {status}\n"
            
    emb = discord.Embed(title=f"🎒 حقيبة {it.user.display_name}", description=desc, color=0x3498db)
    emb.set_footer(text="لتجهيز بانر استخدم: /equip [الرقم]")
    await it.response.send_message(embed=emb)

@bot.tree.command(name="equip", description="تجهيز بانر من حقيبتك")
async def equip(it: discord.Interaction, number: str):
    if not await check_channel(it): return
    
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid}) or {"inventory": ["1"]}
    inv = u.get("inventory", ["1"])
    
    if number not in inv:
        return await it.response.send_message("❌ أنت لا تملك هذا البانر! اذهب للمتجر لشرائه.", ephemeral=True)
    
    collection.update_one({"_id": uid}, {"$set": {"bg_id": number}})
    item_name = STORE_BG.get(number, {}).get('name', 'غير معروف')
    await it.response.send_message(f"✅ تم تجهيز **{item_name}** بنجاح.")

@bot.tree.command(name="store", description="المتجر (يوضح المملوك)")
async def store(it: discord.Interaction):
    if not await check_channel(it): return
    
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid}) or {"inventory": ["1"], "bg_id": "1"}
    inv = u.get("inventory", ["1"])
    current_bg = u.get("bg_id", "1")
    
    embeds = []
    items = list(STORE_BG.items())[:10]
    
    for k, v in items:
        # تحديد الحالة بدقة
        if k == current_bg:
            status = "💠 مجهز حالياً"
            color = 0x3498db # أزرق
        elif k in inv:
            status = "✅ مملوك (موجود في الحقيبة)"
            color = 0x2ecc71 # أخضر
        else:
            status = f"💰 السعر: `{format_num(v['price'])}` XP"
            color = 0x9b59b6 # بنفسجي
            
        emb = discord.Embed(title=f"#{k} | {v['name']}", description=f"**الحالة:** {status}", color=color)
        emb.set_image(url=v['url'])
        
        # تغيير التوجيه حسب الحالة
        if k in inv:
            emb.set_footer(text=f"لتجهيزه اكتب: /equip {k}")
        else:
            emb.set_footer(text=f"للشراء اكتب: /buy {k}")
            
        embeds.append(emb)
    
    await it.response.send_message("🛒 **متجر الخلفيات**", embeds=embeds)

@bot.tree.command(name="buy", description="شراء بانر جديد")
async def buy(it: discord.Interaction, number: str):
    if not await check_channel(it): return
    if number not in STORE_BG: return await it.response.send_message("❌ رقم خاطئ.", ephemeral=True)
    
    uid = str(it.user.id)
    u = collection.find_one({"_id": uid})
    if not u:
        collection.insert_one({"_id": uid, "xp": 0, "inventory": ["1"], "bg_id": "1"})
        u = collection.find_one({"_id": uid})
        
    inv = u.get("inventory", ["1"])
    if number in inv:
        return await it.response.send_message("⚠️ تملك هذا البانر بالفعل! استخدم `/equip` لتجهيزه.", ephemeral=True)
        
    item = STORE_BG[number]
    if u['xp'] < item['price']:
        return await it.response.send_message(f"❌ نقاطك لا تكفي! تحتاج `{format_num(item['price'])}` XP.", ephemeral=True)
        
    collection.update_one({"_id": uid}, {
        "$inc": {"xp": -item['price']},
        "$push": {"inventory": number},
        "$set": {"bg_id": number} # يجهز تلقائياً عند الشراء
    })
    await it.response.send_message(f"🎉 تم شراء وتجهيز **{item['name']}**!")

@bot.tree.command(name="top", description="المتصدرين (بدون بوتات)")
async def top(it: discord.Interaction):
    if not await check_channel(it): return
    await it.response.defer()
    
    # جلب الأعلى نقاطاً
    all_users = collection.find().sort("xp", -1)
    desc = ""
    rank_count = 0
    
    for u in all_users:
        if rank_count >= 10: break
        
        # فحص العضو
        m = it.guild.get_member(int(u["_id"]))
        if not m or m.bot: continue # تجاوز البوتات
        
        rank_count += 1
        
        # الأسهم
        old_data = track_col.find_one({"_id": u["_id"]})
        trend = "🟡"
        if old_data:
            if rank_count < old_data['pos']: trend = "🟢" # صعود
            elif rank_count > old_data['pos']: trend = "🔴" # هبوط
            
        track_col.update_one({"_id": u["_id"]}, {"$set": {"pos": rank_count}}, upsert=True)
        desc += f"{trend} **#{rank_count}** | {m.mention}\n╚ 👑 Lvl {u['level']} | ✨ {format_num(u['xp'])}\n\n"
        
    emb = discord.Embed(title="🏆 المتصدرين", description=desc, color=0xf1c40f)
    await it.followup.send(embed=emb)

# --- 6. التشغيل ---
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    uid = str(msg.author.id)
    now = datetime.now()
    
    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=20): return
    xp_cooldown[uid] = now
    
    u = collection.find_one({"_id": uid})
    if not u:
        u = {"_id": uid, "xp": 0, "level": 0, "msg_count": 0, "start_time": time.time(), "inventory": ["1"], "bg_id": "1"}
        collection.insert_one(u)
        
    new_xp = u['xp'] + random.randint(15, 25)
    new_lvl = min(new_xp // 1000, 50)
    
    collection.update_one({"_id": uid}, {"$set": {"xp": new_xp, "level": new_lvl}, "$inc": {"msg_count": 1}})
    
    if new_lvl > u['level']:
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch:
            time_diff = (time.time() - u.get('start_time', time.time())) / 60
            eff = min(100, int((u.get('msg_count', 1) / (time_diff + 1)) * 10))
            
            emb = discord.Embed(title="🚀 LEVEL UP!", description=f"مبروك {msg.author.mention}!", color=0x00ff00)
            emb.add_field(name="Lv.", value=f"**{new_lvl}**", inline=True)
            emb.add_field(name="Rate", value=f"`{eff}%`", inline=True)
            emb.set_thumbnail(url=msg.author.display_avatar.url)
            emb.set_image(url=RANK_IMAGES.get(new_lvl, RANK_IMAGES[5]))
            
            await ch.send(f"{msg.author.mention}", embed=emb)
            
            if new_lvl in LEVEL_ROLES:
                role = msg.guild.get_role(LEVEL_ROLES[new_lvl])
                if role: 
                    try: await msg.author.add_roles(role)
                    except: pass
            collection.update_one({"_id": uid}, {"$set": {"msg_count": 0, "start_time": time.time()}})

    await bot.process_commands(msg)

app = Flask('')
@app.route('/')
def home(): return "OK"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
