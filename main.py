import discord
from discord.ext import commands
import os, json, random, asyncio
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# --- الإعدادات والربط ---
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

# الاتصال بـ MongoDB
cluster = MongoClient(MONGO_URL)
db = cluster["SkyData"] # اسم قاعدة البيانات
collection = db["rank_system"] # اسم الجدول

# إعدادات الغرف والرتب (نفس إعداداتك السابقة)
UPGRADE_CH_ID = 1448638848803405852
ALLOWED_RANK_CH_ID = 1448805638686769213

# دالة جلب بيانات المستخدم من السحاب
def get_user(uid):
    user = collection.find_one({"_id": uid})
    if not user:
        user = {"_id": uid, "xp": 0, "level": 0}
        collection.insert_one(user)
    return user

# دالة تحديث البيانات في السحاب
def save_user(uid, xp, level):
    collection.update_one({"_id": uid}, {"$set": {"xp": xp, "level": level}})

# --- كود البوت ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="rank", description="عرض بطاقة مستواك")
async def rank(interaction: discord.Interaction):
    if interaction.channel_id != ALLOWED_RANK_CH_ID:
        return await interaction.response.send_message("❌ استخدم الأمر في الغرفة المخصصة", ephemeral=True)
    
    await interaction.response.defer()
    u = get_user(str(interaction.user.id))
    
    embed = discord.Embed(title=f"📊 رتبة {interaction.user.display_name}", color=0x9b59b6)
    embed.add_field(name="المستوى", value=f"**{u['level']}**", inline=True)
    embed.add_field(name="الخبرة", value=f"**{u['xp']}**", inline=True)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Sky System (Cloud Saved)")
    await interaction.followup.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot: return
    uid = str(message.author.id)
    u = get_user(uid)
    
    old_lvl = u["level"]
    new_xp = u["xp"] + random.randint(10, 20)
    new_lvl = new_xp // 200
    
    save_user(uid, new_xp, new_lvl)
    
    if new_lvl > old_lvl:
        ch = bot.get_channel(UPGRADE_CH_ID)
        if ch:
            await ch.send(f"🎊 {message.author.mention} مبروك لفل **{new_lvl}**!")
    
    await bot.process_commands(message)

# --- نظام الـ Uptime (Flask) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.run(TOKEN)
