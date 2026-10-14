from time import sleep, strftime
import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os
import mysql.connector
from datetime import datetime

from time_tracking import add_active_session, get_active_sessions, update_time_stat
from user_xp import calculate_total_xp, calculate_voice_xp, calculate_chat_xp, add_xp

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
#handler = logging.FileHandler(filename="audit-bot.log", encoding="utf-8", mode="a")
handler = logging.StreamHandler()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.presences = True


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.dj_bot = None
        self.server = None
        self.spam_cancelled = False
        self.conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_BOT_USER"),
            password=os.getenv("DB_BOT_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        self.cursor = self.conn.cursor()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

        # Initialize server and DJ bot reference
        self.server = self.guilds[0]
        member = self.server.get_member(int(os.getenv("DJ_USER_ID")))

        # Perform a DB sync to ensure all members are in the database
        for member in self.server.members:
            query = """INSERT IGNORE INTO Users (user_id, name, joined_date, xp, user_level, prestige, messages_sent) 
               VALUES(%s, %s, %s, %s, %s, %s, %s);"""

            self.cursor.execute(
                query, (member.id, member.name, member.joined_at, 0, 1, 0, 0)
            )
            self.conn.commit()

        if member:
            self.dj_bot = member

        get_active_sessions(self.server, self.cursor, self.conn)

        # Check if DJ bot is alone
        self.check_dj.start()
        self.stats_command.start()
        self.time_heartbeat.start()

    @tasks.loop(minutes=5)
    async def check_dj(self):
        if self.dj_bot.status == discord.Status.online:
            if self.dj_bot.voice:
                # Disconnect DJ bot if it is alone in a vc
                if self.check_dj_inactivity(self.dj_bot):
                    await self.dj_bot.move_to(None)
                    logging.debug(
                        "Disconnected DJ bot from voice channel due to inactivity"
                    )
        return

    @tasks.loop(minutes=1)
    async def time_heartbeat(self):
        print("Updating heartbeat")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(""" UPDATE VoiceActive SET last_heartbeat = %s;""", (now,))
        self.conn.commit()

    def check_dj_inactivity(self, dj_bot):
        voice_channel = dj_bot.voice.channel
        if len(voice_channel.members) <= 1:
            return True
        return False

    @tasks.loop(minutes=5)
    async def stats_command(self):
        member_count = self.server.member_count
        members_online = 0
        bots = 0

        for member in self.server.members:
            if member.status != discord.Status.offline and not member.bot:
                members_online += 1
            elif member.bot:
                bots += 1
        # total_users_channel = self.server.get_channel(1470283340685901915)
        # await total_users_channel.edit(name=f"📊 | Users: {member_count - bots}")

        # online_users_channel = self.server.get_channel(1470279109203595387)
        # await online_users_channel.edit(name=f"🟢 | Online: {members_online}")

        # bots_channel = self.server.get_channel(1470279218918195272)
        # await bots_channel.edit(name=f"🤖 | Bots: {bots}")


bot = Bot()


# Used to play music with the DJ bot
@bot.command(name="play")
async def wake_bot(ctx, url: str):
    print(ctx.channel)
    if (
        bot.dj_bot.status != discord.Status.online
        and ctx.channel.name == "song-requests"
    ):
        await ctx.send("DJ bot is offline! Waking up DJ...")
        sleep(5)
        await ctx.send(f"!play {url}")
        return


# Used to spam a user x times. Can be cancelled with !cspam command.
@bot.command(name="spam")
async def spam(ctx, user: str, times: int):
    for i in range(times):
        if bot.spam_cancelled:
            bot.spam_cancelled = False
            await ctx.send("Spam cancelled.")
            break
        await ctx.send(f"{user}")
        sleep(2)
    return


# Cancels the spam command
@bot.command(name="cspam")
async def cancel_spam(ctx):
    bot.spam_cancelled = True


# TODO: Used to restart the DJ bot if a problem occurs.
@bot.command(name="restart")
async def restart_dj(ctx, url: str):
    pass


# TODO: Used to update the DJ bot if a new version is released.
@bot.command(name="update")
async def update_dj(ctx, url: str):
    pass


@bot.command(name="xp")
async def check_xp(ctx):
    print("xp")
    query = """SELECT xp FROM Users WHERE user_id = %s;"""
    bot.cursor.execute(query, (ctx.author.id,))
    result = bot.cursor.fetchone()

    if result:
        xp = result[0]
        await ctx.send(f"{ctx.author.mention}, you have {xp} XP!")
    else:
        await ctx.send(f"{ctx.author.mention}, you have 0 XP!")


@bot.command(name="level")
async def check_level(ctx):
    print("level")
    query = """SELECT user_level, prestige FROM Users WHERE user_id = %s;"""
    bot.cursor.execute(query, (ctx.author.id,))
    result = bot.cursor.fetchone()

    if result:
        level, prestige = result

    if level and prestige:
        await ctx.send(
            f"{ctx.author.mention}, you are Prestige {prestige} level {level}!"
        )
    elif level:
        await ctx.send(f"{ctx.author.mention}, you are at level {level}!")
    else:
        await ctx.send(f"{ctx.author.mention}, you are at level 1!")


# When someone joins the server
@bot.event
async def on_member_join(member):
    print(f"{member} has joined the server.")

    query = """INSERT IGNORE INTO Users (user_id, name, joined_date, xp, user_level, prestige, messages_sent) 
               VALUES(%s, %s, %s, %s, %s, %s, %s);"""

    bot.cursor.execute(query, (member.id, member.name, member.joined_at, 0, 1, 0, 0))
    bot.conn.commit()


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel:
        add_active_session(member, bot.cursor, bot.conn)
    elif before.channel and after.channel is None:
        update_time_stat(bot.server, bot.cursor, bot.conn, member.id)


@bot.event
async def on_message(ctx):
    if ctx.author.bot:
        return
    xp = calculate_chat_xp()
    print(f"xp: {xp}")
    add_xp(ctx.author.id, xp, bot.cursor, bot.conn)
    await bot.process_commands(ctx)

    # channel = bot.get_channel(971928329072566336)
    # await channel.send(xp)


bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
