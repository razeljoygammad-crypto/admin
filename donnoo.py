import discord
from discord.ext import commands
from discord import app_commands
import math
from flask import Flask
from threading import Thread

# =========================
# KEEP ALIVE (RENDER FIX)
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()


# =========================
# DISCORD BOT
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
                "⚠️ Numbers only!", ephemeral=True
            )

        # XP CALC
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

        # SAVE DATA
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

        # EMBED
        embed = discord.Embed(
            title="XP Calculator Result",
            color=discord.Color.green() if enough_xp else discord.Color.red(),
            description="✅ Enough XP!" if enough_xp else "❌ Not enough XP!"
        )

        embed.add_field(name="📊 Levels", value=f"{clvl} ➜ {tlvl}", inline=False)
        embed.add_field(name="Total XP", value=f"{total_xp:,}", inline=False)
        embed.add_field(name="📦 Pack", value=f"{self.pack}", inline=False)

        await interaction.response.send_message(embed=embed)


# =========================
# STATUS COMMAND (FIXED)
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

    total_earnings_all = 0

    for user_id, data in user_data.items():
        packs = data["packs"]

        earnings = (
            packs["mini"] * PACK_PRICES["mini"] +
            packs["small"] * PACK_PRICES["small"] +
            packs["mediant"] * PACK_PRICES["mediant"] +
            packs["vast"] * PACK_PRICES["vast"]
        )

        total_earnings_all += earnings

        try:
            user = await bot.fetch_user(user_id)
            name = user.name
        except:
            name = f"User {user_id}"

        embed.add_field(
            name=name,
            value=(
                f"📊 Uploads: {data['total_uploads']}\n"
                f"📦 Mini: {packs['mini']}\n"
                f"📦 Small: {packs['small']}\n"
                f"📦 Mediant: {packs['mediant']}\n"
                f"📦 Vast: {packs['vast']}\n"
                f"💰 Earnings: {earnings}"
            ),
            inline=False
        )

    embed.add_field(
        name="💎 TOTAL EARNINGS",
        value=f"{total_earnings_all}",
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

    global user_data
    user_data.clear()

    await interaction.response.send_message("✅ All data cleared!")


# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# =========================
# RUN BOT
# =========================
keep_alive()
bot.run("YOUR_TOKEN_HERE")