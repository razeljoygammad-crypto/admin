import discord
from discord.ext import commands
from discord import app_commands
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
            "refunds": {
            "mini": 0,
            "small": 0,
            "mediant": 0,
            "vast": 0
        },

            "packs": {
                "mini": 0,
                "small": 0,
                "mediant": 0,
                "vast": 0
            }
        }
    return user_data[user_id]

# =========================
# MODAL (FIXED)
# =========================
class CalcModal(discord.ui.Modal):
    def __init__(self, pack):
        super().__init__(title="XP Calculator")
        self.pack = pack

        self.start_lvl = discord.ui.TextInput(label="Start Level")
        self.current_xp = discord.ui.TextInput(label="Current XP", required=False)
        self.end_lvl = discord.ui.TextInput(label="End Level")
        self.end_xp = discord.ui.TextInput(label="End XP", required=False)

        self.add_item(self.start_lvl)
        self.add_item(self.current_xp)
        self.add_item(self.end_lvl)
        self.add_item(self.end_xp)

    async def on_submit(self, interaction: discord.Interaction):

        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message("❌ Not allowed.", ephemeral=True)

        try:
            clvl = int(self.start_lvl.value)
            xp_had = int(self.current_xp.value or 0)
            elvl = int(self.end_lvl.value)
            end_xp = int(self.end_xp.value or 0)
        except:
            return await interaction.response.send_message("⚠️ Numbers only!", ephemeral=True)

        # XP FORMULA (ONE SYSTEM ONLY)
        total_xp = 0
        lvl = clvl

        while lvl < elvl:
            total_xp += 50 * (lvl * lvl + 2)
            lvl += 1

        total_xp = max(0, total_xp - xp_had + end_xp)

        pack_values = {
            "mini": 125000,
            "small": 250000,
            "mediant": 500000,
            "vast": 1100000
        }

        selected_xp = pack_values.get(self.pack, 0)

        # CORRECT LOGIC
        if selected_xp >= total_xp:
            status = "❌ Not Enough"
            missing_xp = total_xp - selected_xp
            extra_xp = 0
        else:
            status = "✅ Enough"
            missing_xp = 0
            extra_xp = selected_xp - total_xp


        embed = discord.Embed(
            title="🎯 XP Result",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="📊 XP Result",
            value=(
                f"**Total XP Needed:** {total_xp:,}\n"
                f"**Pack:** {self.pack}\n"
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
# REFUND FUNCTIONS
# =========================
async def refund_pack(interaction, pack):
    data = get_user(interaction.user.id)

    data["refunds"][pack] += 1

    await interaction.response.send_message(
        f"✅ {pack.capitalize()} refund recorded.",
        ephemeral=True
    )

class RefundButtons(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    async def interaction_check(self, interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ This refund menu isn't yours.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def refund_mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await refund_pack(interaction, "mini")

    @discord.ui.button(label="Small", style=discord.ButtonStyle.success)
    async def refund_small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await refund_pack(interaction, "small")

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.primary)
    async def refund_mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await refund_pack(interaction, "mediant")

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def refund_vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await refund_pack(interaction, "vast")
        
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

        # Remove ALL buttons first
        await interaction.message.edit(view=None)

        # Then open the modal
        await interaction.response.send_modal(CalcModal("mini"))


    @discord.ui.button(label="Small Pack", style=discord.ButtonStyle.success)
    async def small_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        get_user(interaction.user.id)["packs"]["small"] += 1

        # Remove ALL buttons first
        await interaction.message.edit(view=None)

        # Then open the modal
        await interaction.response.send_modal(CalcModal("small"))

 
    @discord.ui.button(label="Mediant Pack", style=discord.ButtonStyle.primary)
    async def mediant_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        get_user(interaction.user.id)["packs"]["mediant"] += 1

        # Remove ALL buttons first
        await interaction.message.edit(view=None)

        # Then open the modal
        await interaction.response.send_modal(CalcModal("mediant"))

    @discord.ui.button(label="Vast Pack", style=discord.ButtonStyle.danger)
    async def vast_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        get_user(interaction.user.id)["packs"]["vast"] += 1

        # Remove ALL buttons first
        await interaction.message.edit(view=None)

        # Then open the modal
        await interaction.response.send_modal(CalcModal("vast"))

    @discord.ui.button(
        label="🔄 Refund",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def refund_btn(self, interaction: discord.Interaction, button: discord.ui.Button):

        # Remove the main buttons
        await interaction.message.edit(view=None)

        # Open the refund menu
        await interaction.response.send_message(
            "Choose which pack to refund:",
            view=RefundButtons(self.author),
            ephemeral=True
        )
        

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
        await bot.process_commands(message)
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
        "mini": 15,
        "small": 25,
        "mediant": 35,
        "vast": 60
    }

    emoji = "<:dl:1495834832524021962>"

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
    refunds = data.get("refunds", {})

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
            f"💰 **Earnings:** {earnings} {emoji}\n"
            f"📊 **Total Uploads:** {data.get('total_uploads', 0)}\n\n"

            f"📦 **Packs**\n"
            f"🚀 Mini: {packs.get('mini', 0)}\n"
            f"🌿 Small: {packs.get('small', 0)}\n"
            f"🔥 Mediant: {packs.get('mediant', 0)}\n"
            f"👑 Vast: {packs.get('vast', 0)}\n\n"

            f"🔄 **Refunds**\n"
            f"🚀 Mini: {refunds.get('mini', 0)}\n"
            f"🌿 Small: {refunds.get('small', 0)}\n"
            f"🔥 Mediant: {refunds.get('mediant', 0)}\n"
            f"👑 Vast: {refunds.get('vast', 0)}"
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed)
    
# =========================
# /COLLECT USER
# =========================
@bot.tree.command(name="collect", description="Clear a specific user's data (Owner only)")
@app_commands.describe(user="The user whose data you want to clear")
async def collect(interaction: discord.Interaction, user: discord.User):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Owner only.",
            ephemeral=True
        )

    data = user_data.get(user.id)

    if not data:
        return await interaction.response.send_message(
            "⚠️ User has no data.",
            ephemeral=True
        )

    packs = data.get("packs", {})
    refunds = data.get("refunds", {})

    PACK_PRICES = {
        "mini": 15,
        "small": 25,
        "mediant": 30,
        "vast": 60
    }

    PACK_PROFIT = {
        "mini": 3.5,
        "small": 4.5,
        "mediant": 6,
        "vast": 12
    }

    PACK_UNCLEAN = {
        "mini": 975,
        "small": 1625,
        "mediant": 2745,
        "vast": 5345
    }

    total_clean = 0
    total_profit = 0
    total_earnings = 0
    total_unclean = 0
    total_refunds = 0

    pack_lines = ""
    refund_lines = ""

    # =========================
    # REFUNDS
    # =========================
    for pack, count in refunds.items():
        total_refunds += count

        if count > 0:
            refund_lines += f"🔄 {pack.capitalize()} × {count}\n"

    # =========================
    # PACKS
    # =========================
    for pack, count in packs.items():

        price = PACK_PRICES.get(pack, 0)
        profit = PACK_PROFIT.get(pack, 0)
        unclean = PACK_UNCLEAN.get(pack, 0)

        earnings = count * price
        profit_total = count * profit
        unclean_total = count * unclean

        total_clean += count
        total_profit += profit_total
        total_earnings += earnings
        total_unclean += unclean_total

        if count > 0:
            pack_lines += (
                f"📦 **{pack.capitalize()} × {count}**\n"
                f" 💰 Earnings: `{earnings}`\n"
                f" 💵 Profit: `{profit_total}`\n"
                f" 🧹 Unclean: `{unclean_total}`\n\n"
            )

    # =========================
    # EMBED
    # =========================
    embed = discord.Embed(
        title="🧹 Data Cleared Successfully",
        description=f"👤 **User:** {user.mention}",
        color=discord.Color.dark_red()
    )

    embed.add_field(
        name="📦 Pack Details",
        value=pack_lines if pack_lines else "No packs recorded.",
        inline=False
    )

    embed.add_field(
        name="🔄 Refund Details",
        value=refund_lines if refund_lines else "No refunds recorded.",
        inline=False
    )

    embed.add_field(
        name="🧮 Summary",
        value=(
            f"📦 Total Packs: `{total_clean}`\n"
            f"🔄 Total Refunds: `{total_refunds}`\n"
            f"💰 Total Earnings: `{total_earnings}`\n"
            f"💵 Total Profit: `{total_profit}`\n"
            f"🧹 Total Unclean: `{total_unclean}`"
        ),
        inline=False
    )

    embed.set_footer(text=f"Cleared by {interaction.user.name}")

    # Delete data AFTER making the embed
    del user_data[user.id]

    await interaction.response.send_message(embed=embed)
    

# =========================
# /COLLECTPRO USER
# =========================
@bot.tree.command(name="collectpro", description="Clear a specific user's data (Owner only)")
@app_commands.describe(user="The user whose data you want to clear")
async def collectpro(interaction: discord.Interaction, user: discord.User):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Owner only.",
            ephemeral=True
        )

    data = user_data.get(user.id)

    if not data:
        return await interaction.response.send_message(
            "⚠️ User has no data.",
            ephemeral=True
        )

    packs = data.get("packs", {})
    refunds = data.get("refunds", {})

    PACK_PRICES = {
        "mini": 15,
        "small": 25,
        "mediant": 35,
        "vast": 60
    }

    PACK_PROFIT = {
        "mini": 3.75,
        "small": 5,
        "mediant": 9,
        "vast": 17
    }

    PACK_UNCLEAN = {
        "mini": 450,
        "small": 575,
        "mediant": 1045,
        "vast": 1845
    }

    total_clean = 0
    total_profit = 0
    total_earnings = 0
    total_unclean = 0
    total_refunds = 0

    pack_lines = ""
    refund_lines = ""

    # =========================
    # REFUND DETAILS
    # =========================
    for pack, count in refunds.items():
        total_refunds += count

        if count > 0:
            refund_lines += f"🔄 {pack.capitalize()} × {count}\n"

    # =========================
    # PACK DETAILS
    # =========================
    for pack, count in packs.items():

        price = PACK_PRICES.get(pack, 0)
        profit = PACK_PROFIT.get(pack, 0)
        unclean = PACK_UNCLEAN.get(pack, 0)

        earnings = count * price
        profit_total = count * profit
        unclean_total = count * unclean

        total_clean += count
        total_profit += profit_total
        total_earnings += earnings
        total_unclean += unclean_total

        if count > 0:
            pack_lines += (
                f"📦 **{pack.capitalize()} × {count}**\n"
                f" 💰 Earnings: `{earnings}`\n"
                f" 💵 Profit: `{profit_total}`\n"
                f" 🧹 Unclean: `{unclean_total}`\n\n"
            )

    # =========================
    # EMBED
    # =========================
    embed = discord.Embed(
        title="🧹 Pro Data Cleared Successfully",
        description=f"👤 **User:** {user.mention}",
        color=discord.Color.dark_red()
    )

    embed.add_field(
        name="📦 Pack Details",
        value=pack_lines if pack_lines else "No packs recorded.",
        inline=False
    )

    embed.add_field(
        name="🔄 Refund Details",
        value=refund_lines if refund_lines else "No refunds recorded.",
        inline=False
    )

    embed.add_field(
        name="🧮 Summary",
        value=(
            f"📦 Total Packs: `{total_clean}`\n"
            f"🔄 Total Refunds: `{total_refunds}`\n"
            f"💰 Total Earnings: `{total_earnings}`\n"
            f"💵 Total Profit: `{total_profit}`\n"
            f"🧹 Total Unclean: `{total_unclean}`"
        ),
        inline=False
    )

    embed.set_footer(text=f"Cleared by {interaction.user.name}")

    # Delete user data AFTER creating the embed
    del user_data[user.id]

    await interaction.response.send_message(embed=embed)
    
# =========================
# READY
# =========================
@bot.event
async def on_ready():
    global OWNER_ID

    app_info = await bot.application_info()
    OWNER_ID = app_info.owner.id

    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} commands")
    print(f"🤖 Logged in as {bot.user}")

# =========================
# LEADERBOARD CHECK
# =========================

def is_owner_check(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID

# =========================
# /LEADERBOARD (OWNER ONLY + PROFIT)
# =========================
@bot.tree.command(name="leaderboard", description="View top users")
@app_commands.check(is_owner_check)
async def leaderboard(interaction: discord.Interaction):

    if not user_data:
        return await interaction.response.send_message(
            "⚠️ No data available.",
            ephemeral=True
        )

    PACK_PRICES = {
        "mini": 15,
        "small": 25,
        "mediant": 35,
        "vast": 60
    }

    PACK_PROFIT = {
        "mini": 3.5,
        "small": 4.5,
        "mediant": 6.5,
        "vast": 15
    }

    PACK_UNCLEAN = {
        "mini": 975,
        "small": 1625,
        "mediant": 2795,
        "vast": 5645
    }

    leaderboard_list = []

    for user_id, data in user_data.items():
        packs = data.get("packs", {})

        earnings = sum(
            packs.get(p, 0) * PACK_PRICES[p]
            for p in PACK_PRICES
        )

        uploads = data.get("total_uploads", 0)

        leaderboard_list.append((user_id, earnings, uploads, packs))

    leaderboard_list.sort(key=lambda x: x[1], reverse=True)
    top_users = leaderboard_list[:10]

    embed = discord.Embed(
        title="🏆 Leaderboard (Top 10)",
        color=discord.Color.gold()
    )

    description = ""

    # ✅ define emoji ONCE here (cleaner)
    emoji = "<:dl:1495834832524021962>"

    for i, (user_id, earnings, uploads, packs) in enumerate(top_users, start=1):
        user = bot.get_user(user_id)
        name = user.name if user else f"User {user_id}"

        medal = ["🥇", "🥈", "🥉"]
        prefix = medal[i-1] if i <= 3 else f"#{i}"

        # 📦 PACK COUNTS
        mini = packs.get("mini", 0)
        small = packs.get("small", 0)
        mediant = packs.get("mediant", 0)
        vast = packs.get("vast", 0)

        # 💵 PROFIT CALCULATION
        mini_profit = mini * PACK_PROFIT["mini"]
        small_profit = small * PACK_PROFIT["small"]
        mediant_profit = mediant * PACK_PROFIT["mediant"]
        vast_profit = vast * PACK_PROFIT["vast"]

        # 💵 UNCLEAN CALCULATION
        mini_unclean = mini * PACK_UNCLEAN["mini"]
        small_unclean = small * PACK_UNCLEAN["small"]
        mediant_unclean = mediant * PACK_UNCLEAN["mediant"]
        vast_unclean = vast * PACK_UNCLEAN["vast"]

        total_profit = mini_profit + small_profit + mediant_profit + vast_profit

        description += (
            f"{prefix} **{name}**\n"
            f"💰 Earnings: {earnings} {emoji} | 📊 {uploads}\n"
            f"💵 Profit: {total_profit} {emoji}\n\n"
            f"🧹 unclean: {mini_unclean + small_unclean + mediant_unclean + vast_unclean} {emoji}\n"
            f" Mini:{mini} Small:{small} Mediant:{mediant} Vast:{vast}\n"
        )

    embed.description = description or "No data."

    await interaction.response.send_message(embed=embed)

# =========================
# ERROR HANDLER (HIDE COMMAND)
# =========================
@leaderboard.error
async def leaderboard_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.CheckFailure):
        return  # silently ignore

# =========================
# command
# =========================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    print(f"ERROR: {error}")
    
    if interaction.response.is_done():
        await interaction.followup.send(f"⚠️ Error: {error}", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Error: {error}", ephemeral=True)

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
