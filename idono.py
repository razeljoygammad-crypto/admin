import discord
from discord.ext import commands
from discord import app_commands
import math
from flask import Flask
import os
from threading import Thread
import asyncio

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
OWNER_ID = 1465712809928036434  # 🔴 PUT YOUR DISCORD ID HERE

# =========================
# STORAGE
# =========================
user_data = {}
processed_messages = set()

# =========================
# CHECKS
# =========================
def has_allowed_role(member: discord.Member):
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

def is_owner(user: discord.User):
    return user.id == OWNER_ID

# =========================
# CLEAR COMMANDS
# =========================
@bot.tree.command(name="clear", description="Clear ALL data (Owner only)")
async def clear(interaction: discord.Interaction):
    if not is_owner(interaction.user):
        return await interaction.response.send_message(
            "❌ Only the owner can use this command.",
            ephemeral=True
        )

    user_data.clear()

    await interaction.response.send_message(
        "🧹 All data cleared!",
        ephemeral=True
    )

@bot.tree.command(name="clear_user", description="Clear a specific user's data (Owner only)")
@app_commands.describe(user="User to clear")
async def clear_user(interaction: discord.Interaction, user: discord.User):

    if not is_owner(interaction.user):
        return await interaction.response.send_message(
            "❌ Only the owner can use this command.",
            ephemeral=True
        )

    if user.id in user_data:
        del user_data[user.id]

        await interaction.response.send_message(
            f"🧹 Cleared data for {user.mention}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "ℹ️ No data found for that user.",
            ephemeral=True
        )

# =========================
# MODAL
# =========================
class CalcModal(discord.ui.Modal):

    def __init__(self, pack):
        super().__init__(title='XP & Pack Calculator')
        self.pack = pack

        self.start_lvl = discord.ui.TextInput(label='Current Level')
        self.current_xp = discord.ui.TextInput(label='Current XP', required=False)
        self.end_lvl = discord.ui.TextInput(label='End Level')
        self.end_xp = discord.ui.TextInput(label='End XP', required=False)

        self.add_item(self.start_lvl)
        self.add_item(self.current_xp)
        self.add_item(self.end_lvl)
        self.add_item(self.end_xp)

    async def on_submit(self, interaction: discord.Interaction):

        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message(
                "❌ You are not allowed to use this.",
                ephemeral=True
            )

        try:
            clvl = int(self.start_lvl.value)
            elvl = int(self.end_lvl.value)
            xp_had = int(self.current_xp.value or 0)
            end_xp = int(self.end_xp.value or 0)
        except ValueError:
            return await interaction.response.send_message(
                "⚠️ Numbers only!",
                ephemeral=True
            )

        total_xp = 0
        lvl = clvl

        while lvl < elvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        total_xp -= xp_had
        total_xp -= end_xp
        total_xp = max(0, total_xp)

        pack_values = {
            "mini": 125_000,
            "small": 250_000,
            "mediant": 500_000,
            "vast": 1_000_000
        }

        selected_xp = pack_values.get(self.pack.lower(), 0)

        enough_xp = selected_xp >= total_xp

        if enough_xp:
            color = discord.Color.red()
            status = "❌ Not enough XP!"
        else:
            color = discord.Color.green()
            status = "✅ Enough XP!"

        embed = discord.Embed(
            title="📊 XP Result",
            description=status,
            color=color
        )

        embed.add_field(name="📊 Total XP", value=f"{total_xp:,} XP", inline=False)
        embed.add_field(name="📊 Levels", value=f"{clvl} ➜ {elvl}", inline=False)
        embed.add_field(name="📦 Pack", value=f"{self.pack} ({selected_xp:,} XP)", inline=False)

        if enough_xp:
            )
            embed.add_field(
                name="⚠️ XP Missing",
                value=f"{total_xp - selected_xp:,} XP needed",
                inline=False
            )
        else:
            embed.add_field(
                name="🎉 Extra XP",
                value=f"+{selected_xp - total_xp:,} XP remaining",
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
            await interaction.response.send_message("❌ Not your calculator!", ephemeral=True)
            return False

        if not has_allowed_role(interaction.user):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return False

        return True

    @discord.ui.button(label="Mini Pack", style=discord.ButtonStyle.success)
    async def mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal("mini"))

    @discord.ui.button(label="Small Pack", style=discord.ButtonStyle.success)
    async def small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal("small"))

    @discord.ui.button(label="Mediant Pack", style=discord.ButtonStyle.primary)
    async def mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal("mediant"))

    @discord.ui.button(label="Vast Pack", style=discord.ButtonStyle.danger)
    async def vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal("vast"))

# =========================
# IMAGE DETECTION (FIXED)
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not has_allowed_role(message.author):
        return

    # 🔒 LOCK FIRST (prevents duplicate triggers)
    if message.id in processed_messages:
        return

    processed_messages.add(message.id)

    # Check for image
    has_image = False
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image"):
            has_image = True
            break

    if not has_image:
        processed_messages.discard(message.id)
        return

    await message.reply(
        "🖼️ Image detected!",
        view=ImageButtons(message.author),
        mention_author=False
    )

    await asyncio.sleep(10)
    processed_messages.discard(message.id)

    await bot.process_commands(message)

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("TOKEN"))
