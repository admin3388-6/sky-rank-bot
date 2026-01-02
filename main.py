import discord
from discord.ext import commands
from discord import app_commands
import os, random, asyncio
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from datetime import datetime, timedelta

# --- الإعدادات والربط ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"]
collection = db["rank_system"]

UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213

LEVEL_ROLES = {
    10: 1448821273756172348,
    20: 1448821177605947402,
    30: 1448821103391674398,
    40: 1448821022462709891,
    50: 1448820918490239027
}

xp_cooldown = {}

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

def get_user(uid):
    user = collection.find_one({"_id": uid})
    if not user:
        user = {"_id": uid, "xp": 0, "level": 0}
        collection.insert_one(user)
    return user

def save_user(uid, xp, level):
    collection.update_one({"_id": uid}, {"$set": {"xp": xp, "level": level}})

class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = SkyBot()

# --- أوامر الإدارة (للمسؤولين فقط) ---

@bot.tree.command(name="give_xp", description="إضافة نقاط XP لمستخدم")
@app_commands.checks.has_permissions(administrator=True)
async def give_xp(interaction: discord.Interaction, member: discord.Member, amount: int):
    u = get_user(str(member.id))
    new_xp = u["xp"] + amount
    new_lvl = new_xp // 250
    save_user(str(member.id), new_xp, new_lvl)
    await interaction.response.send_message(f"✅ تم إضافة `{amount}` نقطة لـ {member.mention}. المستوى الحالي: `{new_lvl}`")

@bot.tree.command(name="set_level", description="تعديل لفل مستخدم مباشرة")
@app_commands.checks.has_permissions(administrator=True)
async def set_level(interaction: discord.Interaction, member: discord.Member, level: int):
    new_xp = level * 250
    save_user(str(member.id), new_xp, level)
    await interaction.response.send_message(f"✅ تم تغيير مستوى {member.mention} إلى `{level}`")

# --- أمر /rank ---
@bot.tree.command(name="rank", description="عرض بطاقة مستواك")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    if interaction.channel_id != ALLOWED_RANK_CH_ID:
        return await interaction.response.send_message(f"❌ هذا الأمر متاح فقط في <#{ALLOWED_RANK_CH_ID}>", ephemeral=True)
    
    await interaction.response.defer()
    target = member or interaction.user
    u = get_user(str(target.id))
    
    embed = discord.Embed(title=f"📊 ملف {target.display_name}", color=0x9b59b6)
    embed.add_field(name="المستوى", value=f"⭐ `{u['level']}`", inline=True)
    embed.add_field(name="الخبرة", value=f"✨ `{u['xp']}`", inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_image(url=get_rank_image(u["level"]))
    embed.set_footer(text="Sky Data Elite System", icon_url="https://i.ibb.co/BHy8Kj71/Picsart-25-12-27-23-06-04-733.png")
    await interaction.followup.send(embed=embed)

# --- أمر /top (المتصدرين المحسن) ---
@bot.tree.command(name="top", description="عرض أفضل 10 متفاعلين في السيرفر")
async def top(interaction: discord.Interaction):
    await interaction.response.defer()
    top_users = list(collection.find().sort("xp", -1).limit(10))
    
    embed = discord.Embed(title="🏆 قائمة أساطير Sky Data", color=0xf1c40f)
    
    # إضافة صورة صاحب المركز الأول كصورة مصغرة
    if top_users:
        first_user = interaction.guild.get_member(int(top_users[0]["_id"]))
        if first_user: embed.set_thumbnail(url=first_user.display_avatar.url)

    desc = ""
    for i, user in enumerate(top_users, 1):
        member = interaction.guild.get_member(int(user["_id"]))
        name = member.mention if member else f"مستخدم غادر"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔹"
        desc += f"{medal} **#{i}** | {name}\n└ لفل: `{user['level']}` | خبرة: `{user['xp']}`\n\n"
    
    embed.description = desc or "لا توجد بيانات حالياً"
    embed.set_footer(text="تفاعل أكثر لتظهر في القائمة!")
    await interaction.followup.send(embed=embed)

# --- نظام كسب الـ XP والأدوار ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    
    uid = str(message.author.id)
    now = datetime.now()

    if uid in xp_cooldown and now < xp_cooldown[uid] + timedelta(seconds=30):
        return

    u = get_user(uid)
    old_lvl = u["level"]
    new_xp = u["xp"] + random.randint(15, 25)
    new_lvl = new_xp // 250
    
    save_user(uid, new_xp, new_lvl)
    xp_cooldown[uid] = now

    if new_lvl > old_lvl:
        channel = bot.get_channel(UPGRADE_CH_ID)
        if channel:
            emb = discord.Embed(
                title="🆙 مستوى جديد!",
                description=f"تهانينا {message.author.mention}! لقد وصلت للمستوى **{new_lvl}**",
                color=0x2ecc71
            )
            emb.set_thumbnail(url=get_rank_image(new_lvl))
            await channel.send(embed=emb)
        
        # نظام الأدوار التلقائي
        if new_lvl in LEVEL_ROLES:
            role = message.guild.get_role(LEVEL_ROLES[new_lvl])
            if role:
                try: await message.author.add_roles(role)
                except: print(f"خطأ في إضافة الرتبة لـ {message.author.name}")

    await bot.process_commands(message)

# --- نظام الـ Uptime (Flask) ---
app = Flask('')
@app.route('/')
def home(): return "Sky Rank Bot is Running 24/7!"

def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
