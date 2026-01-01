import discord
from discord.ext import commands
from discord import app_commands, ui
import os, json, random, asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread

# --- الإعدادات ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = "database.json"

def load_db():
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f: return json.load(f)
    except: return {"users": {}, "config": {"welcome_ch": None, "welcome_msg": "نورت السيرفر يا بطل!"}}

def save_db(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# دالة الصور لكل مستوى (حرفياً كما طلبت)
def get_rank_image(level):
    if level <= 5: return "https://i.ibb.co/1tbgDVW9/Picsart-25-12-27-22-57-14-589.png"
    if level <= 15: return "https://i.ibb.co/0RWHYkDD/Picsart-25-12-27-22-57-27-354.png"
    return "https://i.ibb.co/TxWy47mp/Picsart-25-12-27-22-59-03-231.png"

class SkyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # المزامنة لكل السيرفرات لضمان ظهور الأوامر فوراً
        await self.tree.sync()
        print("✅ تم مزامنة الأوامر بنجاح!")

bot = SkyBot()

# --- نظام الترحيب ---
@bot.event
async def on_member_join(member):
    ch_id = db["config"].get("welcome_ch")
    if ch_id:
        channel = bot.get_channel(int(ch_id))
        if channel:
            embed = discord.Embed(title="عضو جديد وصل! 🎉", description=f"أهلاً بك {member.mention} في سيرفرنا!", color=0x00d2ff)
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

# --- أمر Rank المصلح ---
@bot.tree.command(name="rank", description="عرض بطاقتك وتفاعلك")
async def rank(interaction: discord.Interaction):
    await interaction.response.defer()
    uid = str(interaction.user.id)
    u = db["users"].get(uid, {"xp": 0, "level": 0})
    
    embed = discord.Embed(title=f"📊 رتبة {interaction.user.display_name}", color=0x00d2ff)
    embed.add_field(name="المستوى", value=f"⭐ {u['level']}", inline=True)
    embed.add_field(name="الخبرة", value=f"🧩 {u['xp']}", inline=True)
    embed.set_image(url=get_rank_image(u["level"]))
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
    await interaction.followup.send(embed=embed)

# --- تسجيل التفاعل ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    uid = str(message.author.id)
    if uid not in db["users"]: db["users"][uid] = {"xp": 0, "level": 0}
    
    db["users"][uid]["xp"] += random.randint(10, 20)
    if db["users"][uid]["xp"] >= (db["users"][uid]["level"] + 1) * 150:
        db["users"][uid]["level"] += 1
        await message.channel.send(f"🎊 كفو {message.author.mention}! وصلت للمستوى {db['users'][uid]['level']}")
    
    save_db(db)
    await bot.process_commands(message)

# --- API الموقع (مصلح بالكامل) ---
app = Flask(__name__)
CORS(app)

@app.route('/api/full_stats')
def full_stats():
    guild = bot.guilds[0] if bot.guilds else None
    top_list = sorted(db["users"].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    
    # إصلاح هيكل البيانات ليفهمه الموقع
    formatted_top = [[uid, data] for uid, data in top_list]
    
    return jsonify({
        "members": guild.member_count if guild else 0,
        "online": len([m for m in guild.members if m.status != discord.Status.offline]) if guild else 0,
        "servers": len(bot.guilds),
        "channels": [{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels],
        "top_users": formatted_top
    })

@app.route('/api/action', methods=['POST'])
def action():
    data = request.json
    if data['type'] == 'send':
        channel = bot.get_channel(int(data['channel_id']))
        if channel:
            bot.loop.create_task(channel.send(data['content']))
            return jsonify({"status": "ok"})
    return jsonify({"status": "error"})

def run_api():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run_api).start()
    bot.run(TOKEN)
