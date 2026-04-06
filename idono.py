import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread

# =========================
# KEEP ALIVE
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
# CHECK ROLE
# =========================
def has_allowed_role(member: discord.Member):
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

# =========================
# FIX DATA FUNCTION
# =========================
def fix_user_data(data):
    if "packs" not in data:
        data["packs"] = {
            "mini": 0,
            "small": 0,
            "mediant": 0,
            "vast": 0
        }

    if "uploads" not in data:
        data["uploads"] = 0

    if "total_sales" not in data:
        data["total_sales"] = 0

    return data

# =========================
# MODAL
# =========================
class CalcModal(discord.ui.Modal, title='XP & Pack Calculator'):

    def __init__(self, pack):
        super().__init__()
        self.pack = pack

    start_lvl = discord.ui.TextInput(label='Current Level')
    current_xp = discord.ui.TextInput(label='Current XP', required=False)
    end_lvl = discord.ui.TextInput(label='End Level')
    end_xp = discord.ui.TextInput(label='End XP (optional)', required=False)

    async def on_submit(self, interaction: discord.Interaction):

        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message("❌ Not allowed", ephemeral=True)

        try:
            clvl = int(self.start_lvl.value)
            elvl = int(self.end_lvl.value)
            xp_had = int(self.current_xp.value or 0)
            end_xp = int(self.end_xp.value or 0)
        except ValueError:
            return await interaction.response.send_message("⚠️ Numbers only!", ephemeral=True)

        # =========================
        # XP CALCULATION
        # =========================
        total_xp = 0
        lvl = clvl

        while lvl < elvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        total_xp = max(0, total_xp - xp_had + end_xp)

        # =========================
        # PACK VALUES
        # =========================
        pack_values = {
            "mini": 125_000,
            "small": 250_000,
            "mediant": 500_000,
            "vast": 1_000_000
        }

        selected_xp = pack_values[self.pack]

        # ✅ FIXED LOGIC
        enough_xp = total_xp >= selected_xp
      
        # =========================
        # EMBED
        # =========================
        embed = discord.Embed(
            title="📊 Result",
            description="❌ Not enough XP!" if enough_xp else "✅ Enough XP!",
            color=discord.Color.red() if enough_xp else discord.Color.green()
        )

        embed.add_field(name="Levels", value=f"{clvl} ➜ {elvl}", inline=False)
        embed.add_field(name="Total XP", value=f"{total_xp:,}", inline=False)
        embed.add_field(name="Pack", value=self.pack, inline=False)

        if enough_xp:
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
# BUTTONS
# =========================
class ImageButtons(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def mini(self, interaction, button):
        await interaction.response.send_modal(CalcModal("mini"))

    @discord.ui.button(label="Small", style=discord.ButtonStyle.success)
    async def small(self, interaction, button):
        await interaction.response.send_modal(CalcModal("small"))

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.primary)
    async def mediant(self, interaction, button):
        await interaction.response.send_modal(CalcModal("mediant"))

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def vast(self, interaction, button):
        await interaction.response.send_modal(CalcModal("vast"))
        

# =========================
# IMAGE DETECTION (FIXED)
# =========================
processed_messages = set()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not has_allowed_role(message.author):
        return

    # ✅ Must have attachments
    if not message.attachments:
        return

    # ✅ Must contain at least 1 image
    if not any(
        att.content_type and att.content_type.startswith("image")
        for att in message.attachments
    ):
        return

    # ❗ Prevent duplicate responses
    if message.id in processed_messages:
        return

    processed_messages.add(message.id)

    await message.reply(
        "🖼️ Image detected!",
        view=ImageButtons(message.author)
    )

    await bot.process_commands(message)

# =========================
# STATUS COMMAND (FIXED)
# =========================
@bot.tree.command(name="status", description="View stats (user or owner)")
@app_commands.describe(user="User to check (owner only)")
async def status(interaction: discord.Interaction, user: discord.User = None):

    PACK_PRICES = {
        "mini": 7,
        "small": 12,
        "mediant": 17,
        "vast": 30
    }

    # USER MODE
    if user is None:
        uid = str(interaction.user.id)
        data = user_data.get(uid)

        if not data:
            return await interaction.response.send_message("ℹ️ You have no data yet.", ephemeral=True)

        target_user = interaction.user

    # OWNER MODE
    else:
        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("❌ Owner only can check other users.", ephemeral=True)

        uid = str(user.id)
        data = user_data.get(uid)

        if not data:
            return await interaction.response.send_message("ℹ️ That user has no data.", ephemeral=True)

        target_user = user

    data = fix_user_data(data)
    packs = data["packs"]

    earnings = sum(packs[k] * PACK_PRICES[k] for k in PACK_PRICES)

    embed = discord.Embed(
        title=f"📊 Status of {target_user.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(name="📤 Uploads", value=data["uploads"], inline=False)
    embed.add_field(name="📦 Packs", value=str(packs), inline=False)
    embed.add_field(name="💰 Earnings", value=earnings, inline=False)
    embed.add_field(name="💵 Total Sales", value=data.get("total_sales", 0), inline=False)

    await interaction.response.send_message(embed=embed)

    
# =========================
# CLEAR USER
# =========================
@bot.tree.command(name="clear_user", description="Clear a user")
@app_commands.describe(user="User to clear")
async def clear_user(interaction: discord.Interaction, user: discord.User):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)

    if user.id in user_data:
        del user_data[user.id]
        await interaction.response.send_message(
            f"🧹 Cleared {user.mention}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "ℹ️ No data",
            ephemeral=True
        )

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
keep_alive()
bot.run(os.getenv("TOKEN"))
