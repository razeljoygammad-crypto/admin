import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread

# =========================
# KEEP ALIVE (RENDER)
# =========================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run, daemon=True).start()

# =========================
# DISCORD BOT
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CONFIG
# =========================
ALLOWED_CATEGORY_ID = 1467004864272793724
ALLOWED_ROLE_IDS = [1466987521987711047]
OWNER_ID = 1409138196775702599

# =========================
# STORAGE
# =========================
user_data = {}
processed_messages = set()

# =========================
# CHECKS
# =========================
def is_allowed_channel(channel):
    return channel and getattr(channel, "category_id", None) == ALLOWED_CATEGORY_ID

def has_allowed_role(member):
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

def is_owner(user):
    return user.id == OWNER_ID

# =========================
# MODAL
# =========================
class CalcModal(discord.ui.Modal, title='XP Calculator'):

    def __init__(self, pack):
        super().__init__()
        self.pack = pack

    start_lvl = discord.ui.TextInput(label='Current Level')
    current_xp = discord.ui.TextInput(label='Current XP', required=False)
    target_lvl = discord.ui.TextInput(label='Target Level')

    async def on_submit(self, interaction: discord.Interaction):

        if not is_allowed_channel(interaction.channel):
            return await interaction.response.send_message("❌ Wrong category.", ephemeral=True)

        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)

        try:
            clvl = int(self.start_lvl.value)
            tlvl = int(self.target_lvl.value)
            xp_had = int(self.current_xp.value or 0)
        except:
            return await interaction.response.send_message("⚠️ Numbers only!", ephemeral=True)

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

        pack_prices = {"mini": 7, "small": 12, "mediant": 17, "vast": 30}

        selected_xp = pack_values.get(self.pack, 0)

        if total_xp <= selected_xp:
            result_text = "✅ Enough XP!"
            extra_xp = selected_xp - total_xp
        else:
            result_text = "❌ Not enough XP!"
            extra_xp = total_xp - selected_xp

        # SAVE DATA
        uid = interaction.user.id

        if uid not in user_data:
            user_data[uid] = {"packs": {}, "total_uploads": 0, "total_sales": 0}

        user_data[uid]["total_uploads"] += 1
        user_data[uid]["packs"][self.pack] = user_data[uid]["packs"].get(self.pack, 0) + 1
        user_data[uid]["total_sales"] += pack_prices.get(self.pack, 0)

        embed = discord.Embed(title="XP Result", description=result_text)

        embed.add_field(name="Levels", value=f"{clvl} → {tlvl}", inline=False)
        embed.add_field(name="XP Needed", value=f"{total_xp:,}", inline=False)
        embed.add_field(name="Pack XP", value=f"{selected_xp:,}", inline=False)
        embed.add_field(name="Difference", value=f"{extra_xp:,}", inline=False)

        await interaction.response.send_message(embed=embed)

# =========================
# BUTTONS
# =========================
class ImageButtons(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author

    async def interaction_check(self, interaction):
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
# IMAGE DETECTION
# =========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not is_allowed_channel(message.channel):
        return

    if not has_allowed_role(message.author):
        return

    if message.id in processed_messages:
        return

    if not any(att.content_type and "image" in att.content_type for att in message.attachments):
        return

    processed_messages.add(message.id)

    await message.reply("🖼️ Image detected!", view=ImageButtons(message.author))

    await bot.process_commands(message)

# =========================
# STATUS
# =========================
@bot.tree.command(name="status")
@app_commands.describe(user="Owner only")
async def status(interaction: discord.Interaction, user: discord.User = None):

    if interaction.channel.category_id != ALLOWED_CATEGORY_ID:
        return await interaction.response.send_message("❌ Wrong category.", ephemeral=True)

    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    if user and not is_owner(interaction.user):
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

    target = user if user else interaction.user

    data = user_data.get(target.id)
    if not data:
        return await interaction.response.send_message("ℹ️ No data.", ephemeral=True)

    embed = discord.Embed(title=f"📊 {target.name}")
    embed.add_field(name="Uploads", value=data["total_uploads"])
    embed.add_field(name="Sales", value=data["total_sales"])

    await interaction.response.send_message(embed=embed)

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
