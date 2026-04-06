import discord
from discord.ext import commands
from discord import app_commands
import math
from flask import Flask
import os
from threading import Thread

# =========================
# FLASK KEEP-ALIVE
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
OWNER_ID = None

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
            end_xp = int(self.end_xp.value or 0)
        except ValueError:
            return await interaction.response.send_message(
                "⚠️ Numbers only!", ephemeral=True
            )

        # =========================
        # XP CALCULATION
        # =========================
        total_xp = 0
        lvl = clvl

        while lvl < tlvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        # subtract both current XP and end XP
        total_xp = max(0, total_xp - xp_had - end_xp)

        # =========================
        # PACK VALUES
        # =========================
        pack_values = {
            "mini": 125_000,
            "small": 250_000,
            "mediant": 500_000,
            "vast": 1_000_000
        }

        pack_key = self.pack.lower()
        selected_xp = pack_values.get(pack_key, 0)

        # =========================
        # CHECK
        # =========================
        enough_xp = total_xp <= selected_xp

        # =========================
        # SAVE DATA
        # =========================
        user_id = interaction.user.id

        if user_id not in user_data:
            user_data[user_id] = {
                "total_uploads": 0,
                "packs": {
                    "mini": 0,
                    "small": 0,
                    "mediant": 0,
                    "vast": 0
                }
            }

        user_data[user_id]["total_uploads"] += 1

        if pack_key in user_data[user_id]["packs"]:
            user_data[user_id]["packs"][pack_key] += 1

        # =========================
        # EMBED
        # =========================
        if enough_xp:
           color = discord.Color.green()
           status = "✅ Enough XP!"
        else:
            color = discord.Color.red()
            status = "❌ Not enough XP!"

        embed = discord.Embed(
        title="📊 XP Result",
        description=status,
        color=color
        )

        embed.add_field(name="📊 Levels", value=f"{clvl} ➜ {tlvl}", inline=False)
        embed.add_field(name="Total XP Needed", value=f"{total_xp:,}", inline=False)
        embed.add_field(name="📦 Pack", value=f"{self.pack} ({selected_xp:,} XP)", inline=False)

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
                "❌ Not your calculator!", ephemeral=True
            )
            return False

        if not has_allowed_role(interaction.user):
            await interaction.response.send_message(
                "❌ No permission!", ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Mini Pack", style=discord.ButtonStyle.success)
    async def mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("mini"))

    @discord.ui.button(label="Small Pack", style=discord.ButtonStyle.success)
    async def small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("small"))

    @discord.ui.button(label="Mediant Pack", style=discord.ButtonStyle.primary)
    async def mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("mediant"))

    @discord.ui.button(label="Vast Pack", style=discord.ButtonStyle.danger)
    async def vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("vast"))

# =========================
# IMAGE DETECTION
# =========================
processed_messages = set()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not has_allowed_role(message.author):
        return

    # 🚫 Prevent duplicate triggers
    if message.id in processed_messages:
        return

    # ✅ Check if ANY attachment is an image
    has_image = any(
        attachment.content_type and "image" in attachment.content_type
        for attachment in message.attachments
    )

    if has_image:
        processed_messages.add(message.id)

        await message.reply(
            "🖼️ Image detected!",
            view=ImageButtons(message.author)
        )

    await bot.process_commands(message)

# =========================
# STATUS COMMAND
# =========================
@bot.tree.command(name="status", description="View stats")
@app_commands.describe(user="Check user")
async def status(interaction: discord.Interaction, user: discord.Member = None):

    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message(
            "❌ No permission.", ephemeral=True
        )

    if user is None:
        user = interaction.user

    if OWNER_ID is not None:
        if interaction.user.id != OWNER_ID and user != interaction.user:
            return await interaction.response.send_message(
                "❌ You can only view your own data.",
                ephemeral=True
            )

    if user.id not in user_data:
        return await interaction.response.send_message(
            "❌ No data.", ephemeral=True
        )

    data = user_data[user.id]
    packs = data["packs"]

    PACK_PRICES = {
        "mini": 7,
        "small": 12,
        "mediant": 17,
        "vast": 30
    }

    earnings = (
        packs["mini"] * PACK_PRICES["mini"] +
        packs["small"] * PACK_PRICES["small"] +
        packs["mediant"] * PACK_PRICES["mediant"] +
        packs["vast"] * PACK_PRICES["vast"]
    )

    embed = discord.Embed(
        title=f"📊 {user.name}'s Stats",
        color=discord.Color.blurple()
    )

    embed.add_field(name="💰 Earnings", value=f"{earnings} 💎", inline=False)
    embed.add_field(name="📊 Uploads", value=data["total_uploads"], inline=False)

    embed.add_field(
        name="📦 Packs",
        value=(
            f"Mini: {packs['mini']}\n"
            f"Small: {packs['small']}\n"
            f"Mediant: {packs['mediant']}\n"
            f"Vast: {packs['vast']}"
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed)

# =========================
# CLEAR
# =========================
@bot.tree.command(name="clear", description="Clear data")
async def clear(interaction: discord.Interaction):

    if OWNER_ID is not None and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Owner only.", ephemeral=True
        )

    user_data.clear()
    await interaction.response.send_message("✅ All data cleared.")

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
# RUN
# =========================
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("TOKEN"))
