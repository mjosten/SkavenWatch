"""
Program that creates a discord bot that will publish the results of
goonhammer tournaments to a text channel

@author: Michael Josten

"""

#imports 
import asyncio
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from log_utils import setup_logger


load_dotenv()  # can load environment variables into .env file
# example: BOT_TOKEN={your bot token here}

# CONSTANTS
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents) 

logger = setup_logger(__name__)

async def load():
    logger.info("in loading cogs")
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            logger.info(f"Attempting to load {filename[:-3]}")
            await bot.load_extension(f"cogs.{filename[:-3]}")
            logger.info(f"loaded cog: {filename[:-3]}")
        else:
            logger.info("Unable to load pycache folder")

    
async def main():
    # Log in event just to say ready
    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user}")
    
    discord.utils.setup_logging(level=logging.INFO, root=False)
    
    if not BOT_TOKEN:
        logger.error("Unable to get BOT_TOKEN from environment variable")
        raise RuntimeError("Unable to get BOT_TOKEN value from environment variable")
    
    await load()
    await bot.start(BOT_TOKEN)    
    
        
if __name__ == "__main__":
    asyncio.run(main())





