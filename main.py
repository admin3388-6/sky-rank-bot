import discord
from discord.ext import commands
from discord import app_commands, ui
import os, asyncio, json, random
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread

# --- الإعدادات الفنية ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"
IP_CHANNEL_ID = 1448805638686769213

# الأيقونات الثابتة
XP_ICON = "https://i.ibb.co/BHy8Kj71/Picsart-25-12-27-23-06-04-733.png"
LVL_ICON = "https://i.ibb.co/0RR5NMP7/Picsart-25-12-27-23-06-27-356.png"

# --- إدارة البيانات ---
def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"users": {}, "config": {"welcome_ch": None, "bg": "https://i.ibb.co/mVYpF4RQ/Picsart-25-12-24-14-57-39-769.jpg"}}

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- نظام الرتب (الروابط الكاملة حرفياً) ---
def get_rank_image(level):
    if 0 <= level <= 2: return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    elif 3 <= level <= 5: return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    elif 5 <= level <= 8: return "https://i.ibb.co/fztgZ8hG/Picsart-25-12-27-22-57-38-916.png"
    elif 8 <= level <= 10: return "https://i.ibb.co/rfy0BDn6/Picsart-25-12-27-22-58-03-096.png"
    elif 10 <= level <= 13: return "https://i.ibb.co/Wvfqm8v5/Picsart-25-12-27-22-58-10-424.png"
    elif 13 <= level <= 15: return "https://i.ibb.co/0Rrpz67D/Picsart-25-12-27-22-58-15-557.png"
    elif 16 <= level <= 20: return "https://i.ibb.co/hx51cSSB/Picsart-25-12-27-22-58-24-170.png"
    elif 21 <= level <= 25: return "https://i.ibb.co/tpsztsyD/Picsart-25-12-27-22-58-29-156.png"
    elif 26 <= level <= 30: return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    elif 31 <= level <= 35: return "https://i.ibb.co/VWdNG0wf/Picsart-25-12-27-22-58-33-914.png"
    elif 35 <= level <= 38: return "https://i.ibb.co/Q3dnYKDD/Picsart-25-12-27-22-58-41-773.png"
    elif 38 <= level <= 44: return "https://i.ibb.co/Kpt81h1w/Picsart-25-12-27-22-58-48-613.png"
    elif 44 <= level <= 49: return "https://i.ibb.co/xtxVmgN3/Picsart-25-12-27-22-58-53-180.png"
    elif level >= 50: return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"
    return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"

# --- نظام التذاكر ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="اختر نوع التذكرة...",
        options=[
            discord.SelectOption(label="الدعم الفني", emoji="🛠️"),
            discord.SelectOption(label="شكوى", emoji="⚖️"),
            discord.SelectOption(label="مشكلة فنية", emoji="🤖")
        ],
        custom_id="ticket_select"
    )
    async def select_callback(self, interaction, select):
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
        await channel.send(f"أهلاً {interaction.user.mention}، طلبك بخصوص: **{select.values[0]}**")

# --- مشغل البوت ---
class SkyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        # قوة التحديث: مسح شامل ثم مزامنة لضمان عمل الأوامر
        self.add_view(TicketView())
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        print("✅ الأوامر أصبحت حديثة الآن (Outdated Fixed)")

bot = SkyBot()

# --- الأوامر الرئيسية ---
@bot.tree.command(name="rank", description="عرض بطاقة المستوى والرتبة")
async def rank(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0, "messages": 0})
    
    rank_url = get_rank_image(u["level"])
    next_xp = int(150 * (u["level"] ** 1.8) + 100)

    embed = discord.Embed(title=f"📊 رتبة | {interaction.user.display_name}", color=0x00d2ff)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_image(url=rank_url)
    embed.add_field(name="المستوى", value=f"⭐ {u['level']}", inline=True)
    embed.add_field(name="الخبرة", value=f"🧩 {u['xp']} / {next_xp}", inline=True)
    embed.set_footer(text=f"ID: {interaction.user.id}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup", description="تجهيز روم التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 مركز الدعم", description="اختر نوع المساعدة من القائمة.", color=0x2b2d31)
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("تم التجهيز بنجاح!", ephemeral=True)

# --- معالجة الرسائل والـ XP ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    uid = str(message.author.id)
    if uid not in db["users"]: db["users"][uid] = {"xp": 0, "level": 0, "messages": 0}
    
    u = db["users"][uid]
    u["xp"] += random.randint(15, 25)
    u["messages"] += 1
    
    # ترقية المستوى
    next_xp = int(150 * (u["level"] ** 1.8) + 100)
    if u["xp"] >= next_xp and u["level"] < 50:
        u["level"] += 1
        await message.channel.send(f"🎊 كفو {message.author.mention}! ارتقيت للمستوى **{u['level']}**")
    
    save_db(db)
    
    # الردود الذكية في القناة المحددة
    if message.channel.id == IP_CHANNEL_ID:
        replies = {"ip": "الأي بي: `sd2k.progamer.me`", "منور": "نورك يا غالي!"}
        for key, val in replies.items():
            if key in message.content.lower():
                await message.reply(val)
                break

# --- لوحة التحكم (Backend) ---
app = Flask(__name__)
CORS(app)

@app.route('/api/full_stats')
def stats():
    guild = bot.guilds[0] if bot.guilds else None
    top_10 = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    return jsonify({
        "members": guild.member_count if guild else 0,
        "online": 1, # تبسيط للوحة
        "channels": [{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels],
        "top_users": top_10,
        "config": db["config"]
    })

@app.route('/api/action', methods=['POST'])
def action():
    data = request.json
    if data['type'] == 'send':
        ch = bot.get_channel(int(data['channel_id']))
        if ch: bot.loop.create_task(ch.send(data['content']))
    return jsonify({"status": "ok"})

# تشغيل البوت واللوحة
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
bot.run(TOKEN)
