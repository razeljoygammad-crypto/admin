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
OWNER_ID = 1409138196775702599
ALLOWED_CATEGORY_ID = 1467004864272793724
ALLOWED_ROLE_IDS = [1466987521987711047]

# =========================
# STORAGE
# =========================
user_data = {}

# =========================
# HELPERS
# =========================
def has_allowed_role(member: discord.Member):
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

def is_owner(user):
    return user.id == OWNER_ID

# =========================
# MODAL
# =========================
class CalcModal(discord.ui.Modal):

    def __init__(self, pack):
        super().__init__(title="XP Calculator")
        self.pack = pack

        self.start_lvl = discord.ui.TextInput(label="Current Level")
        self.current_xp = discord.ui.TextInput(label="Current XP", required=False)
        self.end_lvl = discord.ui.TextInput(label="End Level")
        self.end_xp = discord.ui.TextInput(label="End XP", required=False)

        self.add_item(self.start_lvl)
        self.add_item(self.current_xp)
        self.add_item(self.end_lvl)
        self.add_item(self.end_xp)

    async def on_submit(self, interaction: discord.Interaction):

        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message(
                "❌ Not allowed.", ephemeral=True
            )

        try:
            clvl = int(self.start_lvl.value)
            xp_had = int(self.current_xp.value or 0)
            elvl = int(self.end_lvl.value)

        except:
            return await interaction.response.send_message(
                "⚠️ Numbers only!", ephemeral=True
            )

        # XP CALCULATION
        total_xp = 0
        lvl = clvl

        while lvl < elvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        total_xp = max(0, total_xp - xp_had)

        pack_values = {
            "mini": 125000,
            "small": 250000,
            "mediant": 500000,
            "vast": 1000000
        }

        selected_xp = pack_values.get(self.pack, 0)
        packs_needed = math.ceil(total_xp / selected_xp) if selected_xp else 0

        embed = discord.Embed(
            title="XP Result",
            color=discord.Color.green()
        )

        embed.add_field(name="Total XP Needed", value=f"{total_xp:,}", inline=False)
        embed.add_field(name="Pack", value=self.pack, inline=False)
        embed.add_field(name="Packs Needed", value=packs_needed, inline=False)

        await interaction.response.send_message(embed=embed)

# =========================
# BUTTON VIEW (FINAL SAFE)
# =========================
class ImageButtons(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author

    async def interaction_check(self, interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            return False

        if not has_allowed_role(interaction.user):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return False

        return True

    @discord.ui.button(label="Mini Pack", style=discord.ButtonStyle.success)
    async def mini_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.edit(view=None)
        except:
            pass
        await interaction.response.send_modal(CalcModal("mini"))

    @discord.ui.button(label="Small Pack", style=discord.ButtonStyle.success)
    async def small_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.edit(view=None)
        except:
            pass
        await interaction.response.send_modal(CalcModal("small"))

    @discord.ui.button(label="Mediant Pack", style=discord.ButtonStyle.primary)
    async def mediant_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.edit(view=None)
        except:
            pass
        await interaction.response.send_modal(CalcModal("mediant"))

    @discord.ui.button(label="Vast Pack", style=discord.ButtonStyle.danger)
    async def vast_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.edit(view=None)
        except:
            pass
        await interaction.response.send_modal(CalcModal("vast"))


# =========================
# IMAGE DETECTION (FINAL CLEAN)
# =========================
import time
from collections import defaultdict

last_trigger = defaultdict(float)

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        await bot.process_commands(message)
        return

    # Only run logic if allowed
    if (
        message.channel.category_id == ALLOWED_CATEGORY_ID
        and has_allowed_role(message.author)
    ):
        now = time.time()

        # cooldown
        if now - last_trigger[message.author.id] >= 3:

            has_image = any(
                att.content_type and "image" in att.content_type.lower()
                for att in message.attachments
            )

            if has_image:
                last_trigger[message.author.id] = now

                await message.reply(
                    f"🖼️ {len(message.attachments)} image(s) detected!",
                    view=ImageButtons(message.author)
                )

    # Always allow commands
    await bot.process_commands(message)
    
# =========================
# /STATUS
# =========================
@bot.tree.command(name="status", description="View upload stats")
@app_commands.describe(user="(Owner only) Check another user")
async def status(interaction: discord.Interaction, user: discord.User = None):

    # =========================
    # PERMISSION CHECK
    # =========================
    if not has_allowed_role(interaction.user) and not is_owner(interaction.user):
        return await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

    PACK_PRICES = {
        "mini": 7,
        "small": 12,
        "mediant": 17,
        "vast": 30
    }

    # =========================
    # OWNER CHECK TARGET USER
    # =========================
    if user:

        if not is_owner(interaction.user):
            return await interaction.response.send_message(
                "❌ Only the owner can check other users.",
                ephemeral=True
            )

        data = user_data.get(user.id)

        if not data:
            return await interaction.response.send_message(
                "❌ This user has no stats yet.",
                ephemeral=True
            )

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

        embed = discord.Embed(
            title="📊 User Statistics",
            color=discord.Color.gold()
        )

        embed.add_field(
            name=user.name,
            value=(
                f"💰 Earnings: {earnings} 💎\n"
                f"📊 Total Uploads: {data.get('total_uploads', 0)}\n"
                f"📦 Mini: {mini}\n"
                f"📦 Small: {small}\n"
                f"📦 Mediant: {mediant}\n"
                f"📦 Vast: {vast}"
            ),
            inline=False
        )

        return await interaction.response.send_message(embed=embed, ephemeral=True)

    # =========================
    # NORMAL USER (SELF ONLY)
    # =========================
    user_id = interaction.user.id
    data = user_data.get(user_id)

    if not data:
        return await interaction.response.send_message(
            "❌ You have no stats yet.",
            ephemeral=True
        )

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

    embed = discord.Embed(
        title="📊 Your Upload Statistics",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name=interaction.user.name,
        value=(
            f"💰 Earnings: {earnings} 💎\n"
            f"📊 Total Uploads: {data.get('total_uploads', 0)}\n"
            f"📦 Mini: {mini}\n"
            f"📦 Small: {small}\n"
            f"📦 Mediant: {mediant}\n"
            f"📦 Vast: {vast}"
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# =========================
# CLEAR COMMAND (OWNER)
# =========================
@bot.tree.command(name="clear", description="Clear all data (Owner only)")
async def clear(interaction: discord.Interaction):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Only owner can use this.",
            ephemeral=True
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
# RUN BOT
# =========================
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("TOKEN"))
