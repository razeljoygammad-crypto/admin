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
    t = Thread(target=run)
    t.daemon = True
    t.start()

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
ALLOWED_CATEGORY_ID = 1467004864272793724  # 🔴 CHANGE THIS
ALLOWED_ROLE_IDS = [1466987521987711047]
OWNER_ID = 1409138196775702599

# =========================
# STORAGE
# =========================
user_data = {}
processed_messages = set()

# =========================
# ROLE CHECK
# =========================
def is_allowed_channel(channel: discord.abc.GuildChannel):
    return channel.category_id == ALLOWED_CATEGORY_ID
    
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
        
         # 🔴 CATEGORY CHECK
        if not is_allowed_channel(interaction.channel):
            return await interaction.response.send_message(
                "❌ This bot only works in the allowed category.",
                ephemeral=True
            )
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

        pack_key = self.pack.lower()
        selected_xp = pack_values.get(pack_key, 0)

        # =========================
        # EXTRA / MISSING XP LOGIC
        # =========================
        if total_xp <= selected_xp:
            enough_xp = True
            extra_xp = selected_xp - total_xp
            missing_xp = 0
        else:
            enough_xp = False
            missing_xp = total_xp - selected_xp
            extra_xp = 0

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
                },
                "total_sales": 0
            }

        user_data[user_id]["total_uploads"] += 1

        if pack_key in user_data[user_id]["packs"]:
            user_data[user_id]["packs"][pack_key] += 1

        user_data[user_id]["total_sales"] += pack_prices.get(pack_key, 0)

        # =========================
        # EMBED
        # =========================
        embed = discord.Embed(
            title="XP Calculator Result",
            description="❌ Not enough XP!" if enough_xp else "✅ Enough XP!",
            color=discord.Color.red() if enough_xp else discord.Color.green()
        )

        embed.add_field(name="📊 Levels", value=f"{clvl} ➜ {tlvl}", inline=False)
        embed.add_field(name="Total XP Needed", value=f"{total_xp:,}", inline=False)
        embed.add_field(name="📦 Pack XP", value=f"{selected_xp:,}", inline=False)

        # =========================
        # FIXED LOGIC
        # =========================
        if enough_xp:
            missing_xp = total_xp - selected_xp
            embed.add_field(name="⚠️ Missing XP", value=f"{missing_xp:,}", inline=False)
        else:
            extra_xp = selected_xp - total_xp
            embed.add_field(name="🎉 Extra XP", value=f"{extra_xp:,}", inline=False)

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
            await interaction.response.send_message("❌ Not yours!", ephemeral=True)
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
# IMAGE DETECTION
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    # 🔴 CATEGORY CHECK HERE
    if not is_allowed_channel(message.channel):
        return

    if message.id in processed_messages:
        return

    if not has_allowed_role(message.author):
        return

    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image"):
                processed_messages.add(message.id)

                await message.reply(
                    "🖼️ Image detected!",
                    view=ImageButtons(message.author)
                )
                break

    await bot.process_commands(message)

# =========================
# STATUS COMMAND
# =========================
@bot.tree.command(name="status", description="View user stats")
@app_commands.describe(user="User to check (owner only)")
async def status(interaction: discord.Interaction, user: discord.User = None):

    # 🔴 SAFE CATEGORY CHECK
    if not interaction.channel or interaction.channel.category_id != ALLOWED_CATEGORY_ID:
        return await interaction.response.send_message(
            "❌ Use this inside the allowed category.",
            ephemeral=True
        )

    member = interaction.user

    # =========================
    # 🔥 OWNER BYPASS (FIRST)
    # =========================
    if member.id == OWNER_ID:
        pass  # owner skips everything
    else:
        # =========================
        # ROLE CHECK (NON-OWNER ONLY)
        # =========================
        has_role = isinstance(member, discord.Member) and any(
            role.id in ALLOWED_ROLE_IDS for role in member.roles
        )

        if not has_role:
            return await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )

    # =========================
    # TARGET USER LOGIC
    # =========================
    if user is not None:
        if member.id != OWNER_ID:
            return await interaction.response.send_message(
                "❌ Only the owner can check other users.",
                ephemeral=True
            )
        target = user
    else:
        target = member

    # =========================
    # DATA CHECK
    # =========================
    data = user_data.get(target.id)

    if not data:
        return await interaction.response.send_message(
            f"ℹ️ No data found for {target.name}.",
            ephemeral=True
        )

    # =========================
    # CALCULATIONS
    # =========================
    PACK_PRICES = {"mini": 7, "small": 12, "mediant": 17, "vast": 30}

    packs = data.get("packs", {})
    uploads = data.get("total_uploads", 0)

    earnings = sum(packs.get(k, 0) * PACK_PRICES[k] for k in PACK_PRICES)

    pack_text = "\n".join([f"{k.capitalize()}: {v}" for k, v in packs.items()]) or "No packs yet"

    # =========================
    # EMBED
    # =========================
    embed = discord.Embed(
        title=f"📊 Status of {target.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(name="📤 Uploads", value=f"{uploads:,}", inline=False)
    embed.add_field(name="📦 Packs", value=pack_text, inline=False)
    embed.add_field(name="💰 Earnings", value=f"{earnings:,}", inline=False)
    embed.add_field(name="💵 Total Sales", value=f"{total_sales:,}", inline=False)

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
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# =========================
# RUN
# =========================
keep_alive()
bot.run(os.getenv("TOKEN"))
