import discord
import os
from discord.ext import commands
from flask import Flask, jsonify, request
from flask_cors import CORS
from threading import Thread

# --- إعدادات البوت ---
token = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)
CORS(app)

# 1. جلب القنوات تلقائياً
@app.route('/get_channels')
def get_channels():
    channels_list = []
    for guild in bot.guilds:
        for channel in guild.text_channels:
            channels_list.append({
                "id": str(channel.id),
                "name": f"{guild.name} | #{channel.name}"
            })
    return jsonify(channels_list)

# 2. استقبال بيانات الإيمباد وإرسالها
@app.route('/send_embed', methods=['POST'])
def send_embed():
    data = request.json
    try:
        channel = bot.get_channel(int(data['channel_id']))
        embed = discord.Embed(
            title=data['title'], 
            description=data['description'], 
            color=int(data['color'].lstrip('#'), 16)
        )
        if data.get('image_url'):
            embed.set_image(url=data['image_url'])
        
        embed.set_footer(text="Sky Data System", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        
        bot.loop.create_task(channel.send(embed=embed))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    if token:
        bot.run(token)
