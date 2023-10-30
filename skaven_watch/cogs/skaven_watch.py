"""
Skaven Watch Cog: Functionality for SkavenWatch Bot

Commands:
/start
/stop
/status
/timetil
/purge
/get

(unlisted)
/ping
/test_watch
"""
#imports 
import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from datetime import date, time, datetime

from skaven_scrape import get_current_skaven_message
from log_utils import setup_logger


# Constants
TIME = time(hour=15)

logger = setup_logger(__name__)


class SkavenWatch(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("SkavenWatch.py is ready")
        try:
            synced = await self.bot.tree.sync()
            logger.info(f"Synced {len(synced)} commands")
            for s in synced:
                logger.info(f"synced command: {s}")
        except:
            logger.error("Unable to sync commands")
        await self.bot.change_presence(status=discord.Status.online, activity=discord.CustomActivity("Waiting to `/start`"))
        
    # Main functionality -> Loop daily and send message if new goonhammer article exists
    @tasks.loop(time=TIME)
    async def send_daily_message(self, channel):
        if channel:
            message = get_current_skaven_message()
            if message:
                logger.info(f"Sending Message:\n{message}")
                await channel.send(message)
            else:
                logger.info("No Article today")
        else:
            logger.error("Error with Channel")
                
    @send_daily_message.before_loop
    async def before_send_daily_message(self):
        await self.bot.wait_until_ready()
        
    # Commands Start
    @app_commands.command(name='start',
                          description="Begin-start SkavenWatch")
    async def start(self, interaction: Interaction):
        if self.send_daily_message.is_running():  # if already running, status report
            logger.info("Daily Message Task is currently running...")
            await interaction.response.send_message(
                embed=discord.Embed(title='SkavenWatch Status',
                                    description="Already Scurry-Running!"
                                    ))
            
        else:
            # if not currently running, start
            await self.bot.change_presence(status=discord.Status.online, activity=discord.CustomActivity("Scurry-Running!"))
            logger.info("starting SkavenWatch daily message task")
            await interaction.response.send_message(
                embed=discord.Embed(title='SkavenWatch Status',
                                    description="Starting SkavenWatch!")
            )
            await self.send_daily_message.start(interaction.channel)
    
    # Commands Stop    
    @app_commands.command(name='stop',
                          description="Stop SkavenWatch (use `/start` to restart)")
    async def stop(self, interaction: Interaction):
        logger.info("Stopping skaven watch")
        logger.info(f"daily_send_message object: {self.send_daily_message}")
        self.send_daily_message.cancel()  # doesn't use await
        
        if self.send_daily_message.is_running():  # if currently running, stop
            await self.bot.change_presence(status=discord.Status.online, activity=discord.CustomActivity("Waiting to `/start`"))
            self.send_daily_message.cancel()
            await interaction.response.send_message(
                embed=discord.Embed(title='SkavenWatch Status',
                                    description="Stopping SkavenWatch!"))
            
        else:  # not running, status report
            await interaction.response.send_message(
                embed=discord.Embed(
                    title='SkavenWatch Status',
                    description="NOT Currently Scurry-Running"
                    ))
        
    # command get
    # gets most recent goonhammer skaven list
    @app_commands.command(name='get', 
                          description="Get the most recent Skaven Lists")
    async def get(self, interaction: Interaction):
        logger.info("Getting most recent skaven list")
        await interaction.response.defer(thinking=True)
        message = get_current_skaven_message(debug=True)
        if message:
            logger.info("sending message")
            await interaction.followup.send(message)
        else:
            logger.error("Unable to get message in GET command")
            await interaction.followup.send("Something went wrong with SkavenWatch")
         
    # command Status
    # messages current status of daily send message loop
    @app_commands.command(name='status',
                          description='Check status of SkavenWatch')
    async def status(self, interaction: Interaction):
        logger.info("Checking SkavenWatch Daily Loop Status")
        if self.send_daily_message.is_running():
            logger.info("Daily Message Task is currently running...")
            await interaction.response.send_message(
                embed=discord.Embed(title='SkavenWatch Status',
                                    description="Currently Scurry-Running!"
                                    ))
        else:
            logger.info("Daily Message Task is NOT currently running.")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title='SkavenWatch Status',
                    description="NOT Currently Scurry-Running\n try using `/start`"
                    ))
            
    # command purge: deletes bot messages
    @app_commands.command(name='purge', description='Deletes all messages from SkavenWatch')
    @commands.has_permissions(manage_messages=True)
    async def purge(self, interaction: Interaction):
        try:
            # check only that the purged messages are from the bot
            def is_bot(m):
                return (m.author.name == "SkavenWatch") and not (interaction.message == m)
            
            if interaction and interaction.channel:
                await interaction.response.defer(thinking=True)
                
                deleted = await interaction.channel.purge(check=is_bot,  # type: ignore
                                                        bulk=True, reason='Purging SkavenWatch Messages',
                                                        limit=100)
                
            else:
                logger.warning("In command /purge: Interaction object is None")
                return
                
        except discord.Forbidden as x:
            logger.error(x)
            await interaction.followup.send("You (or the bot) does not have proper permission", 
                                                    ephemeral=True)
        except discord.HTTPException as x:
            logger.error(x)
            await interaction.followup.send("Purging Failed from HTTP request", 
                                                    ephemeral=True)
        else:
            await interaction.followup.send(f"Deleted {len(deleted)} message(s)")
            
    # Command timetil
    # Gets a time until the next check for goonhammer
    @app_commands.command(name='timetil', description="Get the time until the next check")
    async def timetil(self, interaction: Interaction):
        logger.info("Checking time until daily message")
        if self.send_daily_message.is_running():
            # calculate time remaining until TIME
            now = datetime.now()
            target_datetime = datetime.combine(now.date(), TIME)
            time_remaining = target_datetime - now

            # extract hours and minutes from the time remaining
            hours, remainder = divmod(time_remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            await interaction.response.send_message(embed=discord.Embed(
                title=f"Time Remaining",
                description=f"{hours:02d} hours : {minutes:02d} minutes"
            ))
        
        else:
            logger.warn("SkavenWatch not currently running")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title='SkavenWatch Status',
                    description="NOT Currently Scurry-Running\n try using `/start`"
                    ))
            
    # Commands Test (unlisted)
    @commands.command(name='test_watch', 
                          description="Test Skaven Watcher by getting the most recent lists")
    async def test(self, ctx):
        logger.info("Testing skaven watch")
        
        await ctx.defer(ephemeral=True)
        
        # cant respond twice
        #await interaction.response.send_message("Testing Bot: please wait...")
        message = get_current_skaven_message(debug=True)
        if message:
            logger.info(f"message:\n{message}")
            await ctx.send(message, ephemeral=True)
            # await interaction.response.send_message(message)
        else:
            logger.error("Something went wrong with SkavenWatch Test")
            # await interaction.response.send_message("Something went wrong...")
            await ctx.send("Something went wrong", ephemeral=True)
            
    # Simple test to see if the bot can respons to commands
    # command ping (unlisted)
    @commands.command(name='ping',
                      description='Ping the bot server for latency in Milliseconds')
    async def ping(self, ctx) -> None: 
        bot_latency  = round(self.bot.latency * 1000)
        await ctx.send(f"Latency: {bot_latency} ms")
    

async def setup(bot):
    await bot.add_cog(SkavenWatch(bot))