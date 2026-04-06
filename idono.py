import discord
from discord.ext import commands
from discord import app_commands
import math
from flask import Flask
import os
from threading import Thread
import time
from collections import defaultdict

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
last_trigger = defaultdict(float)

# =========================
# HELPERS
# =========================
def has_allowed_role(member: discord.Member):
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

def is_owner(user):
    return user.id == OWNER_ID

def get_user(user_id):
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
    return user_data[user_id]

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

        # =========================
        # PERMISSION CHECK
        # =========================
        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message(
                "❌ Not allowed.", ephemeral=True
            )

        # =========================
        # INPUT VALIDATION
        # =========================
        try:
            clvl = int(self.start_lvl.value)
            xp_had = int(self.current_xp.value or 0)
            elvl = int(self.end_lvl.value)
        except:
            return await interaction.response.send_message(
                "⚠️ Numbers only!", ephemeral=True
            )

        # =========================
        # XP CALCULATION
        # =========================
        total_xp = 0
        lvl = clvl

        while lvl < elvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        total_xp = max(0, total_xp - xp_had)

        # =========================
        # PACK VALUES
        # =========================
        pack_values = {
            "mini": 125000,
            "small": 250000,
            "mediant": 500000,
            "vast": 1000000
        }

        selected_xp = pack_values.get(self.pack, 0)

        # =========================
        # STATUS LOGIC (IF / ELSE)
        # =========================
        if selected_xp >= total_xp:
            status = "❌ Not Enough"
            missing_xp = total_xp - selected_xp
            extra_xp = 0
        else:
            status = "✅ Enough"
            missing_xp = 0
            extra_xp = selected_xp - total_xp

        # =========================
        # EMBED RESULT
        # =========================
        embed = discord.Embed(
            title="🎯 XP Result",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="📊 XP Result",
            value=(
                f"**Total AXP Got:** {total_xp:,}\n"
                f"**Pack Selected:** {self.pack}\n"
                f"**Status:** {status}\n"
                f"**Missing XP:** {missing_xp:,}\n"
                f"**Extra XP:** {extra_xp:,}"
            ),
            inline=False
        )

        # =========================
        # FOOTER (DYNAMIC)
        # =========================
        if missing_xp > 0:
            embed.set_footer(text="✅ You have enough XP!")
        else:
            embed.set_footer(text=f"👉 You are slightly short by {missing_xp:,} XP")
            

        await interaction.response.send_message(embed=embed)
        
# =========================
# BUTTON VIEW
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
        get_user(interaction.user.id)["packs"]["mini"] += 1
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("mini"))

    @discord.ui.button(label="Small Pack", style=discord.ButtonStyle.success)
    async def small_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        get_user(interaction.user.id)["packs"]["small"] += 1
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("small"))

    @discord.ui.button(label="Mediant Pack", style=discord.ButtonStyle.primary)
    async def mediant_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        get_user(interaction.user.id)["packs"]["mediant"] += 1
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("mediant"))

    @discord.ui.button(label="Vast Pack", style=discord.ButtonStyle.danger)
    async def vast_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        get_user(interaction.user.id)["packs"]["vast"] += 1
        await interaction.message.edit(view=None)
        await interaction.response.send_modal(CalcModal("vast"))

# =========================
# IMAGE DETECTION
# =========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        await bot.process_commands(message)
        return

    if message.channel.category_id != ALLOWED_CATEGORY_ID:
        return

    if not has_allowed_role(message.author):
        return

    now = time.time()

    image_attachments = [
        att for att in message.attachments
        if att.content_type and "image" in att.content_type.lower()
    ]

    # ✅ Only allow 1 to 4 images
    if not (1 <= len(image_attachments) <= 4):
        return

    # ✅ Cooldown to prevent spam/duplicate triggers
    if now - last_trigger[message.author.id] <= 3:
        return

    last_trigger[message.author.id] = now

    # ✅ Update stats
    data = get_user(message.author.id)
    data["total_uploads"] += len(image_attachments)

    # ✅ Show buttons
    await message.reply(
        f"🖼️ {len(image_attachments)} image(s) detected! Choose your pack:",
        view=ImageButtons(message.author)
    )

    await bot.process_commands(message)
# =========================
# /STATUS
# =========================
@bot.tree.command(name="status", description="View upload stats")
@app_commands.describe(user="(Owner only) Check another user")
async def status(interaction: discord.Interaction, user: discord.User = None):

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

    target = interaction.user

    if user:
        if not is_owner(interaction.user):
            return await interaction.response.send_message(
                "❌ Only the owner can check other users.",
                ephemeral=True
            )
        target = user

    data = user_data.get(target.id)

    if not data:
        return await interaction.response.send_message(
            "❌ No stats found.",
            ephemeral=True
        )

    packs = data.get("packs", {})

    earnings = sum(
        packs.get(p, 0) * PACK_PRICES[p]
        for p in PACK_PRICES
    )

    embed = discord.Embed(
        title="📊 User Statistics" if user else "📊 Your Upload Statistics",
        color=discord.Color.gold() if user else discord.Color.blurple()
    )

    embed.add_field(
        name=target.name,
        value=(
            f"💰 Earnings: {earnings} 💎\n"
            f"📊 Total Uploads: {data.get('total_uploads', 0)}\n"
            f"📦 Mini: {packs.get('mini', 0)}\n"
            f"📦 Small: {packs.get('small', 0)}\n"
            f"📦 Mediant: {packs.get('mediant', 0)}\n"
            f"📦 Vast: {packs.get('vast', 0)}"
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed)

 # =========================
# CLEAR COMMAND
# =========================
@bot.tree.command(name="clear", description="Clear data")
async def clear(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)

    user_data.clear()
    await interaction.response.send_message("✅ Data cleared")

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
