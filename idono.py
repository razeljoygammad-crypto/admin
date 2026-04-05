import discord
from discord.ext import commands
from discord import app_commands
import math

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CONFIG
# =========================
ALLOWED_ROLE_IDS = [1466987521987711047]  # 🔁 PUT YOUR ROLE ID
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
        packs_needed = math.ceil(total_xp / selected_xp) if selected_xp > 0 else 0

        # =========================
        # COUNT SYSTEM 🔥
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

        embed.add_field(
            name="📊 Levels",
            value=f"{clvl} ➜ {tlvl}",
            inline=False
        )

        embed.add_field(
            name="Total XP",
            value=f"{total_xp:,}",
            inline=False
        )

        embed.add_field(
            name="📦 Selected Pack",
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
                "❌ This is not your calculator!", ephemeral=True
            )
            return False

        if not has_allowed_role(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission!", ephemeral=True
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
# SLASH COMMAND: STATUS
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
     "mini": 7 ,
     "small": 12 ,
     "mediant": 17 ,
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

    embed.add_field(
        name=f"User {user_id}",
        value=f"💰 Earnings: {earnings} 💎",
        inline=False
    )

    for user_id, data in user_data.items():
        user = await bot.fetch_user(user_id)
        packs = data["packs"]

        embed.add_field(
            name=f"{user.name}",
            value=(
                f"📊 Total Uploads: {data['total_uploads']}\n\n"
                f"📦 Mini: {packs['mini']}\n"
                f"📦 Small: {packs['small']}\n"
                f"📦 Mediant: {packs['mediant']}\n"
                f"📦 Vast: {packs['vast']}"
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# =========================
# /clear COMMAND
# =========================
@bot.tree.command(name="clear", description="Clear all stored data (Owner only)")
async def clear(interaction: discord.Interaction):

    # Owner check
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Only the owner can use this command.",
            ephemeral=True
        )

    # Clear data
    global user_data
    user_data.clear()
    await interaction.response.send_message(
        "✅ DONE COLLECT All DATA ARE CLEARED."
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
import os
bot.run(os.getenv("TOKEN"))
bot.run("token")
