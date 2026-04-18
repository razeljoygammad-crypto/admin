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

        self.start_lvl = discord.ui.TextInput(label="Current Level", required=True)
        self.current_xp = discord.ui.TextInput(label="Current XP", required=True)
        self.end_lvl = discord.ui.TextInput(label="End Level", required=True)
        self.end_xp = discord.ui.TextInput(label="End XP", required=True)

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
            "vast": 1100000
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
        "mini": 12,
        "small": 22,
        "mediant": 28,
        "vast": 55
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
# /COLLECT USER (COOL VERSION)
# =========================
@bot.tree.command(name="collect", description="Clear a specific user's data (Owner only)")
@app_commands.describe(user="The user whose data you want to clear")
async def collect(interaction: discord.Interaction, user: discord.User):

    # Owner check
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Owner only",
            ephemeral=True
        )

    data = user_data.get(user.id)

    if data:

        packs = data.get("packs", {})

        PACK_PRICES = {
            "mini": 12,
            "small": 22,
            "mediant": 28,
            "vast": 55
        }

        PACK_PROFIT = {
            "mini": 2,
            "small": 4,
            "mediant": 5.50,
            "vast": 11
        }
        
        PACK_UNCLEAN = {
            "mini": 1375,
            "small": 2675,
            "mediant": 4680,
            "vast": 9230
        }
        
        total_clean = 0
        total_profit = 0
        total_earnings = 0
        total_unclean = 0

        pack_lines = ""

        for pack, count in packs.items():
            price = PACK_PRICES.get(pack, 0)
            profit = PACK_PROFIT.get(pack, 0)
            unclean = PACK_UNCLEAN.get(pack, 0)

            clean_profit = count * profit
            clean_earnings = count * price
            clean_unclean = count * unclean

            total_clean += count
            total_profit += clean_profit
            total_earnings += clean_earnings
            total_unclean += clean_unclean

            if count > 0:
                pack_lines += (
                    f"📦 **{pack.capitalize()}**: {count}\n"
                    f"  💰 Earnings: `{clean_earnings}`\n"
                    f"  💵 Profit: `{clean_profit}`\n\n"
                    f"  💵 Unclean: `{clean_unclean}`\n\n"
                )

        # delete data
        del user_data[user.id]

        # =========================
        # EMBED OUTPUT
        # =========================
        embed = discord.Embed(
            title="🧹 Data Cleared Successfully",
            description=f"👤 **User:** {user.mention}\n\n📦 **Pack Breakdown:**",
            color=discord.Color.dark_red()
        )

        embed.add_field(
            name="📊 Pack Details",
            value=pack_lines if pack_lines else "No packs found.",
            inline=False
        )

        embed.add_field(
            name="🧮 Summary",
            value=(
                f"💵 **Total Clean:** `{total_clean}`\n"
                f"💰 **Total Earnings:** `{total_earnings}`\n"
                f"💵 **Total Profit:** `{total_profit}`"
                f"💵 **Total Unclean:** `{total_unclean}`"
            ),
            inline=False
        )

        embed.set_footer(text=f"Cleared by {interaction.user.name}")

        await interaction.response.send_message(embed=embed)

    else:
        await interaction.response.send_message(
            "⚠️ User has no data.",
            ephemeral=True
        )
    

# =========================
# /COLLECTPRO USER (COOL VERSION)
# =========================
@bot.tree.command(name="collectpro", description="Clear a specific user's data (Owner only)")
@app_commands.describe(user="The user whose data you want to clear")
async def collectpro(interaction: discord.Interaction, user: discord.User):

    # Owner check
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Owner only",
            ephemeral=True
        )

    data = user_data.get(user.id)

    if data:

        packs = data.get("packs", {})

        PACK_PRICES = {
            "mini": 12,
            "small": 22,
            "mediant": 28,
            "vast": 55
        }

        PACK_PROFIT = {
            "mini": 2.25,
            "small": 4.50,
            "mediant": 6.50,
            "vast": 13
        }
        
        PACK_UNCLEAN = {
            "mini": 850,
            "small": 1625,
            "mediant": 2780,
            "vast": 5430
        }
        
        total_clean = 0
        total_profit = 0
        total_earnings = 0
        total_unclean = 0

        pack_lines = ""

        for pack, count in packs.items():
            price = PACK_PRICES.get(pack, 0)
            profit = PACK_PROFIT.get(pack, 0)
            unclean = PACK_UNCLEAN.get(pack, 0)

            clean_profit = count * profit
            clean_earnings = count * price
            clean_unclean = count * unclean

            total_clean += count
            total_profit += clean_profit
            total_earnings += clean_earnings
            total_unclean += clean_unclean

            if count > 0:
                pack_lines += (
                    f"📦 **{pack.capitalize()}**: {count}\n"
                    f"  💰 Earnings: `{clean_earnings}`\n"
                    f"  💵 Profit: `{clean_profit}`\n\n"
                    f"  💵 Unclean: `{clean_unclean}`\n\n"
                )

        # delete data
        del user_data[user.id]

        # =========================
        # EMBED OUTPUT
        # =========================
        embed = discord.Embed(
            title="🧹 Data Cleared Successfully",
            description=f"👤 **User:** {user.mention}\n\n📦 **Pack Breakdown:**",
            color=discord.Color.dark_red()
        )

        embed.add_field(
            name="📊 Pack Details",
            value=pack_lines if pack_lines else "No packs found.",
            inline=False
        )

        embed.add_field(
            name="🧮 Summary",
            value=(
                f"📦 **Total Pack:** `{total_clean}`\n"
                f"💰 **Total Earnings:** `{total_earnings}`\n"
                f"💵 **Total Profit:** `{total_profit}`\n"
                f"💵 **Total Unclean:** `{total_unclean}`"
            ),
            inline=False
        )

        embed.set_footer(text=f"Cleared by {interaction.user.name}")

        await interaction.response.send_message(embed=embed)

    else:
        await interaction.response.send_message(
            "⚠️ User has no data.",
            ephemeral=True
        )
    
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
        "mini": 12,
        "small": 22,
        "mediant": 28,
        "vast": 55
    }

    # 💵 PROFIT PER PACK
    PACK_PROFIT = {
        "mini": 2,
        "small": 4,
        "mediant": 5.5,
        "vast": 11
    }

    #💵 UNCLEAN PER PACK
    PACK_UNCLEAN = {
        "mini": 1375,
        "small": 2675,
        "mediant": 4680,
        "vast": 9230 
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
            f"💰 Earnings: {earnings} 💎 | 📊 {uploads}\n"
            f"💵 Profit: {total_profit} 💎\n\n"
            f"🧹 unclean: {mini_unclean + small_unclean + mediant_unclean + vast_unclean} 💎\n"
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
# RUN
# =========================
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("TOKEN"))
