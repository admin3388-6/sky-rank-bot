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

# --- الإعدادات الأساسية ---
token = os.getenv('DISCORD_TOKEN')
RULES_CHANNEL_ID = 1448638848513871872
TICKET_CHANNEL_ID = 1448638848803405846
LOG_CHANNEL_ID = 1449057792739508425
CATEGORY_ID = 1453747983530070126

# رولات الإدارة المسموح لها برؤية التذاكر
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

# --- كلاسات نظام التذاكر ---

class CloseTicketModal(ui.Modal, title='سبب إغلاق التذكرة'):
    reason = ui.TextInput(label='سبب الإغلاق (إجباري)', style=discord.TextStyle.paragraph, min_length=5, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("جاري الحفظ وإغلاق التذكرة...", ephemeral=True)
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        
        embed = discord.Embed(title="📝 تقرير إغلاق تذكرة", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="بواسطة", value=interaction.user.mention, inline=True)
        embed.add_field(name="اسم التذكرة", value=interaction.channel.name, inline=True)
        embed.add_field(name="السبب المذكور", value=self.reason.value, inline=False)
        
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.channel.delete()

class TicketControlView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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

        # إعدادات الصلاحيات للقناة الجديدة
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role_id in STAFF_ROLES_IDS:
            role = guild.get_role(role_id)
            if role: overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        embed = discord.Embed(
            title=f"🎫 تذكرة {t_names[t_type]} جديدة",
            description=f"مرحباً {interaction.user.mention}\nلقد فتحت تذكرة بخصوص **{t_names[t_type]}**.\nيرجى كتابة مشكلتك وانتظار الإدارة.\n\nسيتم الرد عليك قريباً.",
            color=0x5865F2
        )
        embed.set_image(url="https://i.ibb.co/9HfG0Lz5/Picsart-25-12-25-15-08-29-765.jpg")
        
        await channel.send(content=f"{interaction.user.mention} | الإدارة", embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"تم فتح تذكرتك: {channel.mention}", ephemeral=True)

class TicketMainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

# --- أحداث البوت ---

@bot.event
async def on_ready():
    bot.add_view(TicketMainView())
    bot.add_view(TicketControlView())
    print(f'Bot {bot.user} is Ready!')

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="🎫 نظام التذاكر | Support System",
        description="**قوانين فتح تكت:**\n1️⃣ عدم منشن الإدارة بكثرة.\n2️⃣ لا تطلب تعويض على شيء ليس غلطتنا.\n3️⃣ انتظر الإدارة ولا تزعجهم.\n4️⃣ عدم فتح تكت لأسباب غبية.\n\nاختر النوع أدناه:",
        color=0x2b2d31
    )
    embed.set_image(url="https://i.ibb.co/9HfG0Lz5/Picsart-25-12-25-15-08-29-765.jpg")
    await ctx.send(embed=embed, view=TicketMainView())

@bot.event
async def on_member_join(member):
    if not welcome_config["channel_id"]: return
    channel = bot.get_channel(int(welcome_config["channel_id"]))
    try:
        bg_res = requests.get(welcome_config["bg_url"])
        bg = Image.open(io.BytesIO(bg_res.content)).convert("RGBA")
        pfp_res = requests.get(member.display_avatar.url)
        pfp = Image.open(io.BytesIO(pfp_res.content)).convert("RGBA")
        
        pfp_size = (271, 271)
        pfp = pfp.resize(pfp_size, Image.LANCZOS)
        mask = Image.new('L', pfp_size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + pfp_size, fill=255)
        pfp_circle = ImageOps.fit(pfp, mask.size, centering=(0.5, 0.5))
        pfp_circle.putalpha(mask)

        bg.paste(pfp_circle, (627, 196), pfp_circle) # الإحداثيات الدقيقة لـ 2K

        with io.BytesIO() as img_bin:
            bg.save(img_bin, 'PNG')
            img_bin.seek(0)
            msg = f"مرحبا بك {member.mention}\nشكرا لانضمامك لـ **{member.guild.name}**\nعددنا الآن: **{member.guild.member_count}**\nقوانيننا: <#{RULES_CHANNEL_ID}>"
            await channel.send(msg, file=discord.File(fp=img_bin, filename='welcome.png'))
    except Exception as e: print(f"Welcome Error: {e}")

# --- واجهة الويب Control Panel ---

@app.route('/get_channels')
def get_ch():
    return jsonify([{"id": str(c.id), "name": f"{c.guild.name} | #{c.name}"} for g in bot.guilds for c in g.text_channels])

@app.route('/save_welcome_settings', methods=['POST'])
def save_wel():
    global welcome_config
    welcome_config.update(request.json)
    return jsonify({"status": "success"})

@app.route('/send_embed', methods=['POST'])
def send_emb():
    data = request.json
    channel = bot.get_channel(int(data['channel_id']))
    embed = discord.Embed(title=data['title'], description=data['description'], color=int(data['color'].lstrip('#'), 16))
    bot.loop.create_task(channel.send(embed=embed))
    return jsonify({"status": "success"})

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(token)
