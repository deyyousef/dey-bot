import discord
import json
import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

TOKEN = os.getenv("TOKEN")
OWNER_ID = 692428722120163413

# الأي دي الخاص بروم اللفل والصور
LEVEL_CHANNEL_ID = 1500560323349053672
# الأي دي الخاص بروم الأوامر (p و t)
COMMAND_CHANNEL_ID = 1500560180763557950

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

DATA_FILE = "levels.json"
BACKGROUND_IMAGE = "level_bg.png"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_font(size):
    try:
        return ImageFont.truetype("Cairo-Bold-2.ttf", size)
    except:
        return ImageFont.load_default()

def make_level_image(member, old_level, new_level):
    bg = Image.open(BACKGROUND_IMAGE).convert("RGBA")
    bg = bg.resize((1280, 720))

    overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, 0, 550, 720), fill=(0, 0, 0, 180))
    bg = Image.alpha_composite(bg, overlay)

    font_title = get_font(110)
    font_name = get_font(85)
    font_level = get_font(95)

    response = requests.get(member.display_avatar.url)
    avatar = Image.open(BytesIO(response.content)).convert("RGBA")
    avatar = avatar.resize((140, 140))

    mask = Image.new("L", (140, 140), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 140, 140), fill=255)

    border = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.ellipse((0, 0, 160, 160), fill=(255, 200, 0, 130))

    bg.paste(border, (450, 270), border)
    bg.paste(avatar, (460, 280), mask)

    draw = ImageDraw.Draw(bg)

    draw.text((60, 55), "Level Up!", font=font_title, fill=(255, 200, 0))
    draw.text((60, 195), member.display_name, font=font_name, fill=(255, 255, 255))
    draw.text((60, 325), f"Level {old_level}", font=font_level, fill=(200, 200, 200))

    draw.line((95, 460, 95, 520), fill=(255, 255, 255), width=8)
    draw.polygon([(78, 520), (112, 520), (95, 560)], fill=(255, 255, 255))

    x, y = 60, 520
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            draw.text((x + dx, y + dy), f"Level {new_level}", font=font_level, fill=(255, 120, 0))

    draw.text((x, y), f"Level {new_level}", font=font_level, fill=(255, 255, 0))

    output = f"levelup_{member.id}.png"
    bg.save(output)
    return output

@client.event
async def on_ready():
    print(f"🔥 Bot is online: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    data = load_data()
    user_id = str(message.author.id)

    if user_id not in data:
        data[user_id] = {"xp": 0, "level": 0}

    content = message.content.lower().strip()
    parts = content.split()

    # secret تجربة فقط بدون XP
    if content == "secret":
        if message.author.id != OWNER_ID:
            return

        current_level = data[user_id]["level"]
        old_level = max(current_level - 1, 0)
        new_level = current_level

        img = make_level_image(message.author, old_level, new_level)
        msg = f"🎉 مبـروك {message.author.mention} وصـلت للفـل رقم {new_level}\nاستمر/ي يا أسطورة 🔥"

        level_channel = client.get_channel(LEVEL_CHANNEL_ID)
        if level_channel:
            await level_channel.send(content=msg, file=discord.File(img))
        else:
            await message.channel.send(content=msg, file=discord.File(img))
        return

    # أمر p
    if parts and parts[0] == "p":
        if message.channel.id != COMMAND_CHANNEL_ID:
            save_data(data)
            return

        target = message.mentions[0] if message.mentions else message.author
        tid = str(target.id)

        if tid not in data:
            data[tid] = {"xp": 0, "level": 0}

        await message.channel.send(
            f"🔥 {target.display_name}\n"
            f"🏆 Level: {data[tid]['level']}\n"
            f"✨ XP: {data[tid]['xp']}/100"
        )

        save_data(data)
        return

    # أمر t
    if content == "t":
        if message.channel.id != COMMAND_CHANNEL_ID:
            save_data(data)
            return

        sorted_users = sorted(
            data.items(),
            key=lambda x: (x[1]["level"], x[1]["xp"]),
            reverse=True
        )

        text = "🏆 **Top 10 Members** 🏆\n\n"
        medals = ["🥇", "🥈", "🥉"]

        for i, (uid, stats) in enumerate(sorted_users[:10], start=1):
            try:
                member = await message.guild.fetch_member(int(uid))
                name = member.display_name
            except:
                name = "Unknown"

            medal = medals[i - 1] if i <= 3 else f"{i}."
            text += f"{medal} {name} — Level `{stats['level']}` | XP `{stats['xp']}/100`\n"

        await message.channel.send(text)
        save_data(data)
        return

    # XP للرسائل العادية فقط
    data[user_id]["xp"] += 5

    if data[user_id]["xp"] >= 100:
        old_level = data[user_id]["level"]
        data[user_id]["xp"] = 0
        data[user_id]["level"] += 1
        new_level = data[user_id]["level"]

        level_channel = client.get_channel(LEVEL_CHANNEL_ID)

        img = make_level_image(message.author, old_level, new_level)
        msg = f"🎉 مبـروك {message.author.mention} وصـلت للفـل رقم {new_level}\nاستمر/ي يا أسطورة 🔥"

        try:
            if level_channel:
                await level_channel.send(content=msg, file=discord.File(img))
            else:
                await message.channel.send(content=msg, file=discord.File(img))
        except:
            await message.channel.send(content=msg, file=discord.File(img))

    save_data(data)

client.run(TOKEN)
