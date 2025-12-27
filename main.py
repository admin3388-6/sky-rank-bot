import discord
from discord.ext import commands
from discord import app_commands, ui
import os, io, requests, asyncio, json, random
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
from PIL import Image, ImageDraw

# --- الإعدادات الفنية الكاملة ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"
IP_CHANNEL_ID = 1448805638686769213

# صور الأيقونات الثابتة ورسوميات الرتب
XP_ICON_URL = "https://i.ibb.co/BHy8Kj71/Picsart-2-12-27-23-06-04-733.png"
LVL_ICON_URL = "https://i.ibb.co/0RR5NMP7/Picsart-25-12-27-23-06-27-356.png"

# --- قاعدة بيانات الرتب والإعدادات ---
def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except: 
        return {
            "users": {}, 
            "config": {
                "welcome_ch": None, 
                "bg": "https://i.ibb.co/mVYpF4RQ/Picsart-25-12-24-14-57-39-769.jpg", 
                "anti_spam": True,
                "smart_reply_enabled": True
            }
        }

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- دالة جلب صورة الرتبة بناءً على المستوى (كاملة بدون اختصار) ---
def get_rank_image(level):
    if 0 <= level <= 2: return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    elif 3 <= level <= 5: return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    elif 6 <= level <= 8: return "https://i.ibb.co/fztgZ8hG/Picsart-25-12-27-22-57-38-916.png"
    elif 9 <= level <= 10: return "https://i.ibb.co/rfy0BDn6/Picsart-25-12-27-22-58-03-096.png"
    elif 11 <= level <= 13: return "https://i.ibb.co/Wvfqm8v5/Picsart-25-12-27-22-58-10-424.png"
    elif 14 <= level <= 15: return "https://i.ibb.co/0Rrpz67D/Picsart-25-12-27-22-58-15-557.png"
    elif 16 <= level <= 20: return "https://i.ibb.co/hx51cSSB/Picsart-25-12-27-22-58-24-170.png"
    elif 21 <= level <= 25: return "https://i.ibb.co/tpsztsyD/Picsart-25-12-27-22-58-29-156.png"
    elif 26 <= level <= 35: return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    elif 36 <= level <= 38: return "https://i.ibb.co/Q3dnYKDD/Picsart-25-12-27-22-58-41-773.png"
    elif 39 <= level <= 44: return "https://i.ibb.co/Kpt81h1w/Picsart-25-12-27-22-58-48-613.png"
    elif 45 <= level <= 49: return "https://i.ibb.co/xtxVmgN3/Picsart-25-12-27-22-58-53-180.png"
    elif level >= 50: return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"
    return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"

# --- نظام التذاكر (UI) ---
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="الدعم الفني", emoji="🛠️", description="للمساعدة التقنية"),
            discord.SelectOption(label="شكوى على شخص", emoji="⚖️", description="تقديم بلاغ"),
            discord.SelectOption(label="مشكلة فنية", emoji="🤖", description="الإبلاغ عن خلل"),
            discord.SelectOption(label="Reset Menu", emoji="🔄", description="تحديث القائمة")
        ]
        super().__init__(placeholder="اختر نوع التذكرة للبدء...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Reset Menu":
            return await interaction.response.send_message("تم التحديث", ephemeral=True)
        
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="TICKETS")
        if not category: category = await guild.create_category("TICKETS")

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
        await interaction.response.send_message(f"تم فتح التذكرة: {channel.mention}", ephemeral=True)
        await channel.send(f"أهلاً {interaction.user.mention}، سيقوم الفريق بالرد عليك قريباً بخصوص: **{self.values[0]}**")

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# --- إعداد البوت ---
class SkyDataBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # حل مشكلة Outdated: مسح وإعادة تزامن الأوامر بالكامل
        self.tree.clear_commands(guild=None)
        self.add_view(TicketView())
        await self.tree.sync()
        print(f"✅ تم تحديث الأوامر بنجاح وحل مشكلة Outdated")

bot = SkyDataBot()

# --- الردود الذكية الشاملة ---
SMART_REPLIES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته، نورتنا!",
    "سلام": "هلا بك، وعليكم السلام والرحمة.",
    "صباح الخير": "صباح النور والسرور، يسعد صباحك!",
    "مساء الخير": "مساء الورد، نورت السيرفر.",
    "شخبارك": "بخير يا وجه الخير، أنت كيفك؟",
    "كيفك": "الحمد لله تمام، طمنا عنك؟",
    "ip": "الأي بي: `sd2k.progamer.me` 🎮",
    "اي بي": "تفضل يا بطل: `sd2k.progamer.me` 🎮",
    "ارحب": "تبقى وتسلم، حياك الله!",
    "كفو": "كفوك الطيب، ما عليك زود.",
    "منور": "النور نورك يا غالي."
    # يمكن التوسع هنا بكلمات أكثر
}

async def process_xp(user):
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"xp": 0, "level": 0, "messages": 0}
    u = db["users"][uid]
    u["xp"] += random.randint(15, 25)
    u["messages"] += 1
    next_xp = int(150 * (u["level"] ** 1.8) + 100)
    if u["xp"] >= next_xp and u["level"] < 50:
        u["level"] += 1
        save_db(db)
        return True
    save_db(db)
    return False

# --- الأوامر ---
@bot.tree.command(name="rank", description="عرض بطاقة مستواك وصورة رتبتك")
async def rank(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0, "messages": 0})
    level = u["level"]
    rank_img = get_rank_image(level)
    next_xp = int(150 * (level ** 1.8) + 100)
    
    embed = discord.Embed(title=f"📊 رتبة {interaction.user.display_name}", color=0x00d2ff)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=rank_img)
    embed.add_field(name="⭐ المستوى", value=f"**{level}**", inline=True)
    embed.add_field(name="🧩 الخبرة", value=f"**{u['xp']} / {next_xp}**", inline=True)
    embed.description = f"**الأيقونات:** [الخبرة]({XP_ICON_URL}) | [المستوى]({LVL_ICON_URL})"
    embed.set_footer(text=f"طلب بواسطة: {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_tickets", description="تجهيز روم التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 مركز التذاكر",
        description="إذا واجهت مشكلة أو تريد تقديم شكوى، اختر النوع من القائمة أدناه.",
        color=0x2b2d31
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("تم التجهيز!", ephemeral=True)

@bot.event
async def on_member_join(member):
    # ترحيب خاص DM
    try:
        embed_dm = discord.Embed(title=f"أهلاً بك في Sky Data!", description="نورتنا يا وحش! تأكد من قراءة القوانين.", color=0x00d2ff)
        await member.send(embed=embed_dm)
    except: pass
    
    # ترحيب عام في القناة
    if db["config"]["welcome_ch"]:
        ch = bot.get_channel(int(db["config"]["welcome_ch"]))
        if ch: await ch.send(f"حياك الله {member.mention} نورتنا!")

@bot.event
async def on_message(message):
    if message.author.bot: return
    if await process_xp(message.author):
        lvl = db["users"][str(message.author.id)]["level"]
        await message.channel.send(f"🎊 {message.author.mention} وصلت للمستوى **{lvl}**!")
    
    if message.channel.id == IP_CHANNEL_ID:
        for key, reply in SMART_REPLIES.items():
            if key in message.content:
                await message.reply(reply)
                break
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"🔥 {bot.user} متصل - السيرفرات: {len(bot.guilds)}")

# --- Dashboard API ---
app = Flask(__name__)
CORS(app)
@app.route('/api/stats')
def stats():
    return jsonify({
        "top_users": sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    })

def run_flask(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_flask).start()
bot.run(TOKEN)
