import discord
from discord.ext import commands
from discord import app_commands, ui
import os, io, requests, asyncio, json, random
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread

# --- الإعدادات الفنية الكاملة ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"
IP_CHANNEL_ID = 1448805638686769213 # قناة الأي بي والردود

# صور الأيقونات الثابتة المطلوبة في البطاقة
XP_ICON_URL = "https://i.ibb.co/BHy8Kj71/Picsart-25-12-27-23-06-04-733.png"
LVL_ICON_URL = "https://i.ibb.co/0RR5NMP7/Picsart-25-12-27-23-06-27-356.png"

# --- إدارة قاعدة البيانات ---
def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
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

# --- دالة جلب صورة الرتبة بناءً على المستوى (بدون اختصار) ---
def get_rank_image(level):
    if 0 <= level <= 2:
        return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    elif 3 <= level <= 5:
        return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    elif 6 <= level <= 8:
        return "https://i.ibb.co/fztgZ8hG/Picsart-25-12-27-22-57-38-916.png"
    elif 9 <= level <= 10:
        return "https://i.ibb.co/rfy0BDn6/Picsart-25-12-27-22-58-03-096.png"
    elif 11 <= level <= 13:
        return "https://i.ibb.co/Wvfqm8v5/Picsart-25-12-27-22-58-10-424.png"
    elif 14 <= level <= 15:
        return "https://i.ibb.co/0Rrpz67D/Picsart-25-12-27-22-58-15-557.png"
    elif 16 <= level <= 20:
        return "https://i.ibb.co/hx51cSSB/Picsart-25-12-27-22-58-24-170.png"
    elif 21 <= level <= 25:
        return "https://i.ibb.co/tpsztsyD/Picsart-25-12-27-22-58-29-156.png"
    elif 26 <= level <= 35:
        return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    elif 36 <= level <= 38:
        return "https://i.ibb.co/Q3dnYKDD/Picsart-25-12-27-22-58-41-773.png"
    elif 39 <= level <= 44:
        return "https://i.ibb.co/Kpt81h1w/Picsart-25-12-27-22-58-48-613.png"
    elif 45 <= level <= 49:
        return "https://i.ibb.co/xtxVmgN3/Picsart-25-12-27-22-58-53-180.png"
    elif level >= 50:
        return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"
    return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"

# --- نظام التذاكر (UI) ---
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="الدعم الفني", emoji="🛠️"),
            discord.SelectOption(label="شكوى على شخص", emoji="⚖️"),
            discord.SelectOption(label="مشكلة فنية", emoji="🤖"),
            discord.SelectOption(label="إعادة ضبط", emoji="🔄", value="reset")
        ]
        super().__init__(placeholder="اختر نوع المساعدة المطلوبة...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "reset":
            return await interaction.response.send_message("تم تحديث القائمة.", ephemeral=True)
        
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
        await interaction.response.send_message(f"تم فتح تذكرتك بنجاح: {channel.mention}", ephemeral=True)
        await channel.send(f"أهلاً {interaction.user.mention}، تم فتح التذكرة بخصوص: **{self.values[0]}**")

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# --- هيكل البوت الرئيسي ---
class SkyDataBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # حل مشكلة Outdated عن طريق مسح الأوامر القديمة كلياً
        self.tree.clear_commands(guild=None)
        self.add_view(TicketView())
        await self.tree.sync()
        print(f"✅ الأوامر محدثة ومتزامنة مع ديسكورد")

bot = SkyDataBot()

# --- معالجة البيانات والردود الذكية ---
SMART_REPLIES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته، نورتنا يا غالي!",
    "سلام": "هلا بك، وعليكم السلام والرحمة.",
    "صباح الخير": "صباح النور والسرور، يسعد صباحك!",
    "مساء الخير": "مساء الورد والجمال، حياك الله.",
    "ip": "تفضل الأي بي يا بطل: `sd2k.progamer.me` 🎮",
    "اي بي": "تفضل الأي بي يا بطل: `sd2k.progamer.me` 🎮",
    "ارحب": "تبقى وتسلم، ترحيبة المطر!",
    "منور": "النور نورك يا وحش."
}

async def add_xp(user):
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"xp": 0, "level": 0, "messages": 0}
    
    u = db["users"][uid]
    u["xp"] += random.randint(15, 25)
    u["messages"] += 1
    
    # حساب المستوى التالي (150 * Level^1.8 + 100)
    needed = int(150 * (u["level"] ** 1.8) + 100)
    
    if u["xp"] >= needed and u["level"] < 50:
        u["level"] += 1
        save_db(db)
        return True
    save_db(db)
    return False

# --- الأوامر المباشرة ---
@bot.tree.command(name="rank", description="عرض بطاقة مستواك وصورتك")
async def rank(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0, "messages": 0})
    
    needed = int(150 * (u["level"] ** 1.8) + 100)
    rank_img = get_rank_image(u["level"])

    embed = discord.Embed(title=f"🛡️ بطاقة التفاعل - {interaction.user.name}", color=0x00d2ff)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=rank_img)
    embed.add_field(name="⭐ المستوى", value=f"**{u['level']}**", inline=True)
    embed.add_field(name="🧩 الخبرة", value=f"**{u['xp']} / {needed}**", inline=True)
    embed.description = f"أيقونة XP: [هنا]({XP_ICON_URL}) | أيقونة Lvl: [هنا]({LVL_ICON_URL})"
    embed.set_footer(text="Sky Data Elite System")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_tickets", description="تجهيز نظام التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 نظام التذاكر", description="اضغط أدناه لفتح تذكرة مساعدة.", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("تم التجهيز.", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    if await add_xp(message.author):
        lvl = db["users"][str(message.author.id)]["level"]
        await message.channel.send(f"🎊 كفو {message.author.mention}! وصلت للمستوى **{lvl}**")

    if message.channel.id == IP_CHANNEL_ID:
        for key, reply in SMART_REPLIES.items():
            if key in message.content:
                await message.reply(reply)
                break
    await bot.process_commands(message)

# --- لوحة التحكم (Backend API) ---
app = Flask(__name__)
CORS(app)

@app.route('/api/full_stats')
def full_stats():
    guild = bot.guilds[0] if bot.guilds else None
    online = len([m for m in guild.members if m.status != discord.Status.offline]) if guild else 0
    
    channels = []
    if guild:
        for c in guild.text_channels:
            channels.append({"id": str(c.id), "name": c.name})

    # تجهيز التوب 10 للوحة التحكم
    top_list = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]

    return jsonify({
        "members": guild.member_count if guild else 0,
        "online": online,
        "servers": len(bot.guilds),
        "channels": channels,
        "top_users": top_list,
        "config": db["config"]
    })

@app.route('/api/action', methods=['POST'])
def action():
    data = request.json
    if data['type'] == 'config':
        db["config"].update(data['payload'])
        save_db(db)
        return jsonify({"status": "ok"})
    elif data['type'] == 'send':
        channel = bot.get_channel(int(data['channel_id']))
        if channel:
            bot.loop.create_task(channel.send(data['content']))
            return jsonify({"status": "ok"})
    return jsonify({"status": "error"})

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
