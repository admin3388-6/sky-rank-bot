import discord
from discord.ext import commands
from discord import app_commands
import os, json, random, asyncio
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread

# --- الإعدادات الأساسية ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"
UPGRADE_CH_ID = 1448638848803405852  # غرفة رسائل الترقية (تظهر فيها الصورة صغيرة)
ALLOWED_RANK_CH_ID = 1448805638686769213 # الغرفة المسموح فيها بـ /rank فقط

# أيقوناتك التي طلبتها
XP_ICON = "https://i.ibb.co/BHy8Kj71/Picsart-25-12-27-23-06-04-733.png"
LVL_ICON = "https://i.ibb.co/0RR5NMP7/Picsart-25-12-27-23-06-27-356.png"

# --- إدارة قاعدة البيانات ---
def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except: return {"users": {}}

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- جلب صورة الرتبة حسب المستوى ---
def get_rank_image(level):
    if 0 <= level <= 2: return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    if 3 <= level <= 5: return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    if 6 <= level <= 8: return "https://i.ibb.co/fztgZ8hG/Picsart-25-12-27-22-57-38-916.png"
    if 9 <= level <= 10: return "https://i.ibb.co/rfy0BDn6/Picsart-25-12-27-22-58-03-096.png"
    if 11 <= level <= 13: return "https://i.ibb.co/Wvfqm8v5/Picsart-25-12-27-22-58-10-424.png"
    if 14 <= level <= 15: return "https://i.ibb.co/0Rrpz67D/Picsart-25-12-27-22-58-15-557.png"
    if 16 <= level <= 20: return "https://i.ibb.co/hx51cSSB/Picsart-25-12-27-22-58-24-170.png"
    if 21 <= level <= 25: return "https://i.ibb.co/tpsztsyD/Picsart-25-12-27-22-58-29-156.png"
    if 26 <= level <= 35: return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    if 36 <= level <= 38: return "https://i.ibb.co/Q3dnYKDD/Picsart-25-12-27-22-58-41-773.png"
    if 39 <= level <= 44: return "https://i.ibb.co/Kpt81h1w/Picsart-25-12-27-22-58-48-613.png"
    if 45 <= level <= 49: return "https://i.ibb.co/xtxVmgN3/Picsart-25-12-27-22-58-53-180.png"
    return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"

class SkyRankBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ نظام الرتب مدمج وجاهز!")

bot = SkyRankBot()

# --- أمر /rank (محصور في الروم المخصص) ---
@bot.tree.command(name="rank", description="معرفة نقاطك التي قمت بتجميعها")
async def rank(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_RANK_CH_ID:
        return await interaction.response.send_message(f"❌ هذا الأمر متاح فقط في الغرفة المخصصة: <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
    
    await interaction.response.defer()
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0})
    
    embed = discord.Embed(title=f"📊 بطاقة رتبة {interaction.user.display_name}", color=0x9b59b6)
    embed.add_field(name="المستوى", value=f"**{u['level']}**", inline=True)
    embed.add_field(name="الخبرة", value=f"**{u['xp']}**", inline=True)
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=get_rank_image(u["level"])) # صورة الرتبة كبيرة هنا
    embed.set_footer(text="Sky Data Elite System", icon_url=XP_ICON)
    
    await interaction.followup.send(embed=embed)

# --- أمر /top المتصدرين ---
@bot.tree.command(name="top", description="عرض قائمة أفضل 10 متفاعلين")
async def top(interaction: discord.Interaction):
    await interaction.response.defer()
    top_list = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 قائمة المتصدرين (Top 10)", color=0xf1c40f)
    desc = ""
    for i, (uid, data) in enumerate(top_list):
        desc += f"**#{i+1}** | <@{uid}> - لفل: `{data['level']}` - نقاط: `{data['xp']}`\n"
    
    embed.description = desc or "لا توجد بيانات حالياً"
    await interaction.followup.send(embed=embed)

# --- أوامر الإدارة (فقط للمسؤولين) ---
@bot.tree.command(name="give", description="إعطاء XP لمستخدم")
@app_commands.checks.has_permissions(administrator=True)
async def give(interaction: discord.Interaction, user: discord.Member, amount: int):
    uid = str(user.id)
    if uid not in db["users"]: db["users"][uid] = {"xp": 0, "level": 0}
    db["users"][uid]["xp"] += amount
    db["users"][uid]["level"] = db["users"][uid]["xp"] // 200
    save_db(db)
    await interaction.response.send_message(f"✅ تم إضافة {amount} XP لـ {user.mention}")

@bot.tree.command(name="set", description="تحديد XP مستخدم")
@app_commands.checks.has_permissions(administrator=True)
async def set_xp(interaction: discord.Interaction, user: discord.Member, amount: int):
    uid = str(user.id)
    db["users"][uid] = {"xp": amount, "level": amount // 200}
    save_db(db)
    await interaction.response.send_message(f"✅ تم تحديد XP {user.mention} بـ {amount}")

@bot.tree.command(name="kill", description="سلب XP من مستخدم")
@app_commands.checks.has_permissions(administrator=True)
async def kill(interaction: discord.Interaction, user: discord.Member, amount: int):
    uid = str(user.id)
    if uid in db["users"]:
        db["users"][uid]["xp"] = max(0, db["users"][uid]["xp"] - amount)
        db["users"][uid]["level"] = db["users"][uid]["xp"] // 200
        save_db(db)
        await interaction.response.send_message(f"⚠️ تم سحب {amount} XP من {user.mention}")

# --- نظام كسب الخبرة والترقية ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    if uid not in db["users"]: db["users"][uid] = {"xp": 0, "level": 0}
    
    old_lvl = db["users"][uid]["level"]
    db["users"][uid]["xp"] += random.randint(5, 15)
    new_lvl = db["users"][uid]["xp"] // 200
    
    if new_lvl > old_lvl:
        db["users"][uid]["level"] = new_lvl
        save_db(db)
        
        # إرسال رسالة الترقية بصورة رتبة صغيرة
        channel = bot.get_channel(UPGRADE_CH_ID)
        if channel:
            emb = discord.Embed(
                description=f"🎊 {message.author.mention} لقد ترقى مستواك من **({old_lvl})** إلى **({new_lvl})**",
                color=0x9b59b6
            )
            emb.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            # هنا جعلنا الصورة صغيرة (Thumbnail) بدلاً من كبيرة
            emb.set_thumbnail(url=get_rank_image(new_lvl))
            await channel.send(content=message.author.mention, embed=emb)
    else:
        save_db(db)
    
    await bot.process_commands(message)

# --- واجهة الموقع ---
app = Flask(__name__)
CORS(app)
@app.route('/api/full_stats')
def full_stats():
    top_list = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    return jsonify({"members": len(db["users"]), "top_users": top_list, "online": 14})

def run_api(): app.run(host='0.0.0.0', port=8080)
if __name__ == "__main__":
    Thread(target=run_api).start()
    bot.run(TOKEN)
