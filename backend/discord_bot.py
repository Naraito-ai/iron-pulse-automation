import os
import asyncio
import logging
import discord
from discord.ext import commands

import database as db
from config import BRAND_NAME

logger = logging.getLogger("discord_bot")

# Create bot instance with necessary intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# We will try to send notifications to this channel if set
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

@bot.event
async def on_ready():
    logger.info(f"✅ Discord Bot logged in as {bot.user}")

@bot.command(name="status")
async def cmd_status(ctx):
    """Check the health of the Iron Pulse backend."""
    try:
        from analytics import get_performance_summary
        stats = get_performance_summary()
        embed = discord.Embed(
            title=f"🟢 {BRAND_NAME} Backend Status",
            color=discord.Color.green()
        )
        embed.add_field(name="Posts Published", value=stats.get("total_posts", 0))
        embed.add_field(name="Total Reach", value=stats.get("total_reach", 0))
        
        # Check token health
        token = db.get_ig_token()
        if token:
            from token_refresher import get_token_info
            info = get_token_info(token)
            health = f"Valid ({info['days_remaining']} days remaining)" if info['is_valid'] else "Expired ❌"
            embed.add_field(name="Token Health", value=health)
        else:
            embed.add_field(name="Token Health", value="Missing ❌")

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error fetching status: {e}")

@bot.command(name="run")
async def cmd_run(ctx):
    """Trigger the pipeline manually."""
    await ctx.send("🚀 Starting Pre-generation Pipeline in background...")
    try:
        from main import run_daily_pregeneration
        asyncio.create_task(asyncio.to_thread(run_daily_pregeneration))
    except Exception as e:
        await ctx.send(f"❌ Error triggering pipeline: {e}")

async def broadcast_log_to_discord(level: str, module: str, message: str):
    """Send a log to the Discord channel if the bot is ready and channel ID is configured."""
    if not bot.is_ready():
        return

    # Try to get channel ID from ENV or DB
    channel_id_str = DISCORD_CHANNEL_ID or db.get_config("DISCORD_CHANNEL_ID")
    if not channel_id_str:
        return

    try:
        channel_id = int(channel_id_str)
        channel = bot.get_channel(channel_id)
        if channel:
            emoji = "✅" if level == "SUCCESS" else "⚠️" if level == "WARNING" else "❌" if level == "ERROR" else "ℹ️"
            if "started" in message.lower() or "trigger" in message.lower():
                emoji = "🚀"
            await channel.send(f"{emoji} **[{module}]** {message}")
    except Exception as e:
        logger.error(f"Failed to send Discord log: {e}")

async def start_discord_bot():
    """Starts the Discord bot as a background task if token exists."""
    token = os.getenv("DISCORD_BOT_TOKEN") or db.get_config("DISCORD_BOT_TOKEN")
    if not token:
        logger.warning("No DISCORD_BOT_TOKEN found. Discord integration disabled.")
        return
    
    logger.info("Starting Discord Bot...")
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Discord Bot failed to start: {e}")

