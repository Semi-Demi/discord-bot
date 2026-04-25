from time import sleep, strftime
import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os
import mysql.connector
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
handler = logging.FileHandler(filename="audit-bot.log", encoding="utf-8", mode="a")

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
            query = """INSERT IGNORE INTO Users (user_id, name, joined_date, xp) 
               VALUES(%s, %s, %s, %s);"""

            self.cursor.execute(query, (member.id, member.name, member.joined_at, 0))
            self.conn.commit()

        if member:
            self.dj_bot = member

        self.get_active_sessions()

        # Check if DJ bot is alone
        self.check_dj.start()
        self.stats_command.start()
        self.time_heartbeat.start()

    def get_active_sessions(self):
        active_users = {}
        rows = []

        # Get the active voice list
        for member in self.server.members:
            if member.voice and member.voice.channel:
                print(f"{member} is in {member.voice.channel} voice channel.")
                active_users[member.id] = member.name

                self.cursor.execute("SELECT user_id FROM VoiceActive")
                rows = self.cursor.fetchall()

        print("Removing any inactive sessions")
        for user in rows:
            if user[0] not in active_users.keys():
                self.update_time_stat(
                    user[0],
                    heartbeat_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.remove_active_session(user[0])
                print(
                    f"User {self.server.get_member(user[0])} - {user[0]}: Removed from VoiceActive table."
                )

        print("Adding any new sessions")
        for user in active_users:
            if user not in [row[0] for row in rows]:
                self.add_active_session(self.server.get_member(user))
                print(
                    f"User {active_users[user]} - {user}: Added to VoiceActive table."
                )

    # Remove user sessions that are no longer active
    def remove_active_session(self, member):
        self.cursor.execute(
            """
            DELETE FROM VoiceActive
            WHERE user_id = %s
            """,
            (member,),
        )
        self.conn.commit()

    # Add new active user sessions
    def add_active_session(self, member):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """INSERT INTO VoiceActive (user_id, channel_id, joined_time, last_heartbeat) 
                    VALUES(%s, %s, %s, %s) ON DUPLICATE KEY UPDATE
                        channel_id = VALUES(channel_id),
                        last_heartbeat = VALUES(last_heartbeat);"""
        self.cursor.execute(query, (member.id, member.voice.channel.id, now, now))
        self.conn.commit()

    def update_time_stat(self, member, heartbeat_time=None):
        if heartbeat_time:
            left_time = heartbeat_time
        else:
            left_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # print(f"{member} has left {before.channel} voice channel at {left_time}.")
        query = """SELECT joined_time FROM VoiceActive WHERE user_id = %s;"""
        bot.cursor.execute(query, (member,))
        result = bot.cursor.fetchone()

        if result:
            joined_time = result[0]
            left_time = datetime.strptime(left_time, "%Y-%m-%d %H:%M:%S")
            time_in_voice = (left_time - joined_time).total_seconds()
            print(
                f"{self.server.get_member(member)} spent {time_in_voice} seconds in voice channel."
            )

            # Update the User's time in voice stats
            query = """INSERT INTO VoiceStats (user_id, date, time_seconds) 
               VALUES(%s, CURDATE(), %s) ON DUPLICATE KEY UPDATE
                time_seconds = time_seconds + VALUES(time_seconds);"""
            bot.cursor.execute(query, (member, time_in_voice))
            bot.conn.commit()

            # Delete the Active Voice session now that User disconnected
            bot.cursor.execute(
                """
                DELETE FROM VoiceActive
                WHERE user_id = %s
            """,
                (member,),
            )

            bot.conn.commit()

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
        bot.cursor.execute(""" UPDATE VoiceActive SET last_heartbeat = %s;""", (now,))
        bot.conn.commit()

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


# When someone joins the server
@bot.event
async def on_member_join(member):
    print(f"{member} has joined the server.")

    query = """INSERT IGNORE INTO Users (user_id, name, joined_date, xp) 
               VALUES(%s, %s, %s, %s);"""

    bot.cursor.execute(query, (member.id, member.name, member.joined_at, 0))
    bot.conn.commit()


@bot.event
async def on_voice_state_update(member, before, after):

    join_time = None
    left_time = None

    if before.channel is None and after.channel:
        join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{member} has joined {after.channel} voice channel at {join_time}.")
        query = """INSERT INTO VoiceActive (user_id, channel_id, joined_time, last_heartbeat) 
               VALUES(%s, %s, %s, %s) ON DUPLICATE KEY UPDATE
                channel_id = VALUES(channel_id),
                joined_time = VALUES(joined_time),
                last_heartbeat = VALUES(last_heartbeat);"""
        bot.cursor.execute(query, (member.id, after.channel.id, join_time, join_time))
        bot.conn.commit()
    elif before.channel and after.channel is None:
        left_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{member} has left {before.channel} voice channel at {left_time}.")
        query = """SELECT joined_time FROM VoiceActive WHERE user_id = %s;"""
        bot.cursor.execute(query, (member.id,))
        result = bot.cursor.fetchone()

        if result:
            joined_time = result[0]
            left_time = datetime.strptime(left_time, "%Y-%m-%d %H:%M:%S")
            time_in_voice = (left_time - joined_time).total_seconds()
            print(f"{member} spent {time_in_voice} seconds in voice channel.")

            # Update the User's time in voice stats
            query = """INSERT INTO VoiceStats (user_id, date, time_seconds) 
               VALUES(%s, CURDATE(), %s) ON DUPLICATE KEY UPDATE
                time_seconds = time_seconds + VALUES(time_seconds);"""
            bot.cursor.execute(query, (member.id, time_in_voice))
            bot.conn.commit()

            # Delete the Active Voice session now that User disconnected
            bot.cursor.execute(
                """
                DELETE FROM VoiceActive
                WHERE user_id = %s
            """,
                (member.id,),
            )

            bot.conn.commit()


bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
