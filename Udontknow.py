import discord
from discord.ext import commands
from discord import app_commands
import math
import os
from motor.motor_asyncio import AsyncIOMotorClient # Async MongoDB driver

# =========================
# CONFIG & DATABASE SETUP
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI") # Get from MongoDB Atlas
ALLOWED_ROLE_ID = 1466987521987711047 
OWNER_ID = 1409138196775702599

# MongoDB Initialization
cluster = AsyncIOMotorClient(MONGO_URI)
db = cluster["bot_database"]
collection = db["user_stats"]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ====================bot.run(TOKEN)=====
# DATABASE UTILITIES
# =========================
async def get_user(user_id):
    user = await collection.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id,
            "total_uploads": 0,
            "packs": {"mini": 0, "small": 0, "mediant": 0, "vast": 0}
        }
        await collection.insert_one(user)
    return user

async def update_user(user_id, pack_key):
    await collection.update_one(
        {"_id": user_id},
        {
            "$inc": {
                "total_uploads": 1,
                f"packs.{pack_key}": 1
            }
        },
        upsert=True
    )

# =========================
# MODAL (Updated for DB)
# =========================
class CalcModal(discord.ui.Modal, title='XP & Pack Calculator'):
    def __init__(self, pack):
        super().__init__()
        self.pack = pack

    start_lvl = discord.ui.TextInput(label='Current Level')
    current_xp = discord.ui.TextInput(label='Current XP', required=False)
    target_lvl = discord.ui.TextInput(label='Target Level')

    async def on_submit(self, interaction: discord.Interaction):
        try:
            clvl, tlvl = int(self.start_lvl.value), int(self.target_lvl.value)
            xp_had = int(self.current_xp.value or 0)
        except ValueError:
            return await interaction.response.send_message("⚠️ Numbers only!", ephemeral=True)

        # XP Calculation logic remains the same
        total_xp = 0
        for lvl in range(clvl, tlvl):
            total_xp += 50 * (lvl * lvl + 2)
        total_xp = max(0, total_xp - xp_had)

        pack_values = {"mini": 125_000, "small": 250_000, "mediant": 500_000, "vast": 1_000_000}
        pack_key = self.pack.lower().replace(" pack", "")
        selected_xp = pack_values.get(pack_key, 0)
        
        # SAVE TO CLOUD DATABASE
        await update_user(interaction.user.id, pack_key)

        status = "✅ Enough XP!" if total_xp <= selected_xp else "❌ Not enough XP!"
        embed = discord.Embed(title="XP Calculator Result", description=status, color=discord.Color.green() if "✅" in status else discord.Color.red())
        embed.add_field(name="📊 Levels", value=f"{clvl} ➜ {tlvl}")
        embed.add_field(name="Total XP Needed", value=f"{total_xp:,}")
        embed.add_field(name="📦 Selected Pack", value=f"{self.pack} ({selected_xp:,} XP)")
        
        await interaction.response.send_message(embed=embed)

# =========================
# VIEW & COMMANDS
# =========================
class ImageButtons(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.author = author

    @discord.ui.button(label="Mini Pack", style=discord.ButtonStyle.success)
    async def mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal(pack="mini"))

    @discord.ui.button(label="Small Pack", style=discord.ButtonStyle.success)
    async def small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal(pack="small"))

    @discord.ui.button(label="Mediant Pack", style=discord.ButtonStyle.primary)
    async def mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal(pack="mediant"))

    @discord.ui.button(label="Vast Pack", style=discord.ButtonStyle.danger)
    async def vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalcModal(pack="vast"))

@bot.event
async def on_message(message):
    if message.author.bot or not any(r.id == ALLOWED_ROLE_ID for r in message.author.roles): return
    if message.attachments and any("image" in a.content_type for a in message.attachments):
        await message.reply("🖼️ Image detected!", view=ImageButtons(message.author))
    await bot.process_commands(message)

@bot.tree.command(name="status", description="View user upload stats")
async def status(interaction: discord.Interaction):
    PACK_PRICES = {"mini": 7, "small": 12, "mediant": 17, "vast": 30}
    embed = discord.Embed(title="📊 User Statistics", color=discord.Color.blue())
    
    # Fetch all data from MongoDB
    cursor = collection.find()
    async for data in cursor:
        user = await bot.fetch_user(data["_id"])
        p = data["packs"]
        earnings = sum(p[k] * PACK_PRICES[k] for k in PACK_PRICES)
        embed.add_field(
            name=f"{user.name}",
            value=f"💰 Earnings: {earnings} 💎\n📦 M: {p['mini']} | S: {p['small']} | Med: {p['mediant']} | V: {p['vast']}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

keep_alive()
token = os.getenv('DISCORD_TOKEN')
client.run(token)
