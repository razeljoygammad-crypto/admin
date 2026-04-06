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
OWNER_ID = 0  # auto-set on ready

# =========================
# STORAGE (PER USER)
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
                "⚠️ Numbers only!", ephemeral=True
            )

        # =========================
        # XP CALC
        # =========================
        total_xp = 0
        lvl = clvl

        while lvl < tlvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        total_xp = max(0, total_xp - xp_had)

        # =========================
        # PACK VALUES
        # =========================
        pack_values = {
            "mini": 125_000,
            "small": 250_000,
            "mediant": 500_000,
            "vast": 1_000_000
        }

        pack_key = self.pack.lower().replace(" pack", "")
        selected_xp = pack_values.get(pack_key, 0)

        # =========================
        # CALCULATIONS
        # =========================
        enough_xp = total_xp <= selected_xp

        # =========================
        # COUNT SYSTEM
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
        # RESULT STATUS
        # =========================
        if enough_xp:
            color = discord.Color.red()
            status = "❌ Not enough XP!"
        else:
            color = discord.Color.green()
            status = "✅ Enough XP!"

        # =========================
        # EMBED
        # =========================
       
        embed = discord.Embed(
            title="XP Calculator Result",
            description=status,
            color=color
        )

        embed.add_field(name="📊 Levels", value=f"{clvl} ➜ {tlvl}", inline=False)
        embed.add_field(name="Total XP", value=f"{total_xp:,}", inline=False)
        embed.add_field(
            name="📦 Pack",
            value=f"{self.pack} ({selected_xp:,} XP)",
            inline=False
        )

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
@bot.tree.command(name="status", description="View user stats")
@app_commands.describe(user="(Owner only) check another user")
async def status(interaction: discord.Interaction, user: discord.Member = None):

    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message(
            "❌ No permission.", ephemeral=True
        )

    if user is None:
        user = interaction.user

    if interaction.user.id != OWNER_ID and interaction.user != user:
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
        packs["mini"] * 7 +
        packs["small"] * 12 +
        packs["mediant"] * 17 +
        packs["vast"] * 30
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

    await interaction.response.send_message(embed=embed, ephemeral=True)

# =========================
# CLEAR (OWNER ONLY)
# =========================
@bot.tree.command(name="clear", description="Clear all data")
async def clear(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
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
