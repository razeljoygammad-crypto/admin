import discord
from discord.ext import commands
from discord import app_commands
import math
from flask import Flask
import os
from threading import Thread

# =========================
# FLASK KEEP-ALIVE SERVER
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CONFIG
# =========================
ALLOWED_ROLE_IDS = [1466987521987711047]
OWNER_ID = 1409138196775702599

# =========================
# STORAGE
# =========================
user_data = {}

# =========================
# ROLE CHECK
# =========================
def has_allowed_role(member: discord.Member):
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

# =========================
# MODAL
# =========================
class CalcModal(discord.ui.Modal, title='XP & Pack Calculator'):

    def __init__(self, pack):
        super().__init__()
        self.pack = pack

    start_lvl = discord.ui.TextInput(label='Current Level')
    current_xp = discord.ui.TextInput(label='Current XP', required=False)
    target_lvl = discord.ui.TextInput(label='Target Level')
    end_xp = discord.ui.TextInput(label='End XP', required=False)

    async def on_submit(self, interaction: discord.Interaction):

        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message(
                "❌ You are not allowed to use this.",
                ephemeral=True
            )

        try:
            clvl = int(self.start_lvl.value)
            tlvl = int(self.target_lvl.value)
            xp_had = int(self.current_xp.value or 0)
        except ValueError:
            return await interaction.response.send_message(
                "⚠️ Numbers only!",
                ephemeral=True
            )

        # XP calculation
        total_xp = 0
        lvl = clvl

        while lvl < tlvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        total_xp = max(0, total_xp - xp_had)

        pack_values = {
            "mini": 125_000,
            "small": 250_000,
            "mediant": 500_000,
            "vast": 1_000_000
        }

        pack_key = self.pack.lower()
        selected_xp = pack_values.get(pack_key, 0)

        enough_xp = total_xp <= selected_xp

        if enough_xp:
            color = discord.Color.red()
            status = "❌ Not enough XP!"
        else:
            color = discord.Color.green()
            status = "✅ Enough XP!"

        embed = discord.Embed(
            title="XP Calculator Result",
            description=status,
            color=color
        )

        embed.add_field(name="📊 Levels", value=f"{clvl} ➜ {tlvl}", inline=False)
        embed.add_field(name="Total XP", value=f"{total_xp:,}", inline=False)
        embed.add_field(name="📦 Selected Pack", value=f"{self.pack} ({selected_xp:,} XP)", inline=False)

        await interaction.response.send_message(embed=embed)

# =========================
# BUTTON VIEW
# =========================
class ImageButtons(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction):

        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ This is not your calculator!",
                ephemeral=True
            )
            return False

        if not has_allowed_role(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission!",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Mini Pack", style=discord.ButtonStyle.success)
    async def mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal(pack="mini"))

    @discord.ui.button(label="Small Pack", style=discord.ButtonStyle.success)
    async def small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal(pack="small"))

    @discord.ui.button(label="Mediant Pack", style=discord.ButtonStyle.primary)
    async def mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal(pack="mediant"))

    @discord.ui.button(label="Vast Pack", style=discord.ButtonStyle.danger)
    async def vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal(pack="vast"))

# =========================
# IMAGE DETECTION
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not has_allowed_role(message.author):
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and "image" in attachment.content_type:
                await message.reply(
                    "🖼️ Image detected!",
                    view=ImageButtons(message.author)
                )

    await bot.process_commands(message)

# =========================
# STATUS COMMAND
# =========================
@bot.tree.command(name="status", description="View user upload stats")
async def status(interaction: discord.Interaction):

    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

    if not user_data:
        return await interaction.response.send_message(
            "❌ No data recorded yet.",
            ephemeral=True
        )

    PACK_PRICES = {
        "mini": 7,
        "small": 12,
        "mediant": 17,
        "vast": 30
    }

    embed = discord.Embed(
        title="📊 User Upload Statistics",
        color=discord.Color.blurple()
    )

    for user_id, data in user_data.items():
        packs = data.get("packs", {})

        mini = packs.get("mini", 0)
        small = packs.get("small", 0)
        mediant = packs.get("mediant", 0)
        vast = packs.get("vast", 0)

        earnings = (
            mini * PACK_PRICES["mini"] +
            small * PACK_PRICES["small"] +
            mediant * PACK_PRICES["mediant"] +
            vast * PACK_PRICES["vast"]
        )

        try:
            user = await bot.fetch_user(user_id)
            username = user.name
        except:
            username = f"User {user_id}"

        embed.add_field(
            name=username,
            value=(
                f"💰 Earnings: {earnings} 💎\n\n"
                f"📊 Total Uploads: {data['total_uploads']}\n"
                f"📦 Mini: {mini}\n"
                f"📦 Small: {small}\n"
                f"📦 Mediant: {mediant}\n"
                f"📦 Vast: {vast}"
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# =========================
# CLEAR COMMAND
# =========================
@bot.tree.command(name="clear", description="Clear all stored data (Owner only)")
async def clear(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Only the owner can use this command.",
            ephemeral=True
        )

    user_data.clear()

    await interaction.response.send_message(
        "✅ ALL DATA CLEARED."
    )

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    global OWNER_ID

    app_info = await bot.application_info()
    OWNER_ID = app_info.owner.id

    await bot.tree.sync()

    print(f"Logged in as {bot.user}")

# =========================
# RUN BOT
# =========================
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("TOKEN"))
