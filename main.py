import discord
import os
import io
import requests
from discord.ext import commands
from discord import ui
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread
from PIL import Image, ImageDraw, ImageOps

# --- الإعدادات ---
token = os.getenv('DISCORD_TOKEN')
RULES_CHANNEL_ID = 1448638848513871872
TICKET_CHANNEL_ID = 1448638848803405846
LOG_CHANNEL_ID = 1449057792739508425
CATEGORY_ID = 1453747983530070126
IP_CHAT_CHANNEL_ID = 1448805638686769213 # قناة الأي بي

STAFF_ROLES_IDS = [1448639184532144128, 1448638848098631881, 1448638848090509381, 
                   1448638848090509380, 1448638848090509379, 1449055160944033934]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
CORS(app)

welcome_config = {"channel_id": None, "bg_url": "https://i.ibb.co/m5m8Z8Y/welcome-bg.jpg"}
ticket_counter = 1

# --- كلاسات التكت ---
class CloseTicketModal(ui.Modal, title='سبب إغلاق التذكرة'):
    reason = ui.TextInput(label='لماذا تريد إغلاق التذكرة؟', style=discord.TextStyle.paragraph, min_length=5, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(title="📝 تقرير إغلاق تذكرة", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="بواسطة", value=interaction.user.mention)
        embed.add_field(name="السبب", value=self.reason.value)
        if log_channel: await log_channel.send(embed=embed)
        await interaction.channel.delete()

class TicketControlView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="إغلاق التذكرة", style=discord.ButtonStyle.danger, custom_id="close_tkt")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CloseTicketModal())

class TicketTypeSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="تبليغ عن شخص", value="report", emoji="⚖️"),
            discord.SelectOption(label="مشكلة", value="problem", emoji="🛠️"),
            discord.SelectOption(label="خطأ Bug", value="bug", emoji="👾"),
        ]
        super().__init__(placeholder="اختر نوع التذكرة...", options=options, custom_id="tkt_select")

    async def callback(self, interaction: discord.Interaction):
        global ticket_counter
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        t_type = self.values[0]
        t_names = {"report": "تبليغ", "problem": "مشكلة", "bug": "خطأ"}
        channel_name = f"{t_names[t_type]}-{ticket_counter:04d}"
        ticket_counter += 1

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for rid in STAFF_ROLES_IDS:
            role = guild.get_role(rid)
            if role: overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        embed = discord.Embed(title=f"🎫 تذكرة {t_names[t_type]}", description=f"مرحباً {interaction.user.mention}، يرجى كتابة تفاصيلك هنا.", color=0x5865F2)
        embed.set_image(url="https://i.ibb.co/9HfG0Lz5/Picsart-25-12-25-15-08-29-765.jpg")
        await channel.send(content=f"{interaction.user.mention} | الإدارة", embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True, delete_after=3)

class TicketMainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

# --- أحداث البوت ---
@bot.event
async def on_ready():
    bot.add_view(TicketMainView())
    bot.add_view(TicketControlView())
    print("Bot is online!")

@bot.event
async def on_message(message):
    if message.author.bot: return
    # نظام الرد التلقائي على الأي بي
    if message.channel.id == IP_CHAT_CHANNEL_ID:
        content = message.content.lower()
        if any(word in content for word in ["ip", "أي بي", "!ip", "اي بي"]):
            await message.reply(f"{message.author.mention} **IP Server:** `sd2k.progamer.me`")
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    if not welcome_config["channel_id"]: return
    channel = bot.get_channel(int(welcome_config["channel_id"]))
    try:
        bg_res = requests.get(welcome_config["bg_url"])
        bg = Image.open(io.BytesIO(bg_res.content)).convert("RGBA")
        pfp_res = requests.get(member.display_avatar.url)
        pfp = Image.open(io.BytesIO(pfp_res.content)).convert("RGBA")
        pfp = pfp.resize((271, 271), Image.LANCZOS)
        mask = Image.new('L', (271, 271), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 271, 271), fill=255)
        pfp.putalpha(mask)
        bg.paste(pfp, (627, 196), pfp)
        with io.BytesIO() as out:
            bg.save(out, format="PNG")
            out.seek(0)
            await channel.send(f"مرحبا بك {member.mention}\nعددنا الآن: **{member.guild.member_count}**", file=discord.File(out, "welcome.png"))
    except: pass

# --- واجهة التحكم ---
@app.route('/get_channels')
def get_ch(): return jsonify([{"id": str(c.id), "name": c.name} for g in bot.guilds for c in g.text_channels])

@app.route('/save_welcome_settings', methods=['POST'])
def save_wel():
    welcome_config.update(request.json)
    return jsonify({"status": "success"})

@app.route('/setup_ticket_panel', methods=['POST'])
def setup_tkt():
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    embed = discord.Embed(title="🎫 نظام التذاكر", description="اختر نوع التذكرة لفتح طلب جديد.", color=0x2b2d31)
    embed.set_image(url="https://i.ibb.co/9HfG0Lz5/Picsart-25-12-25-15-08-29-765.jpg")
    bot.loop.create_task(channel.send(embed=embed, view=TicketMainView()))
    return jsonify({"status": "success"})

def run_web(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_web).start()
bot.run(token)
