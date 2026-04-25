from datetime import datetime
from user_xp import calculate_voice_xp, calculate_chat_xp, add_xp


def get_active_sessions(server, cursor, conn):
    active_users = {}
    rows = []

    # Get the active voice list
    for member in server.members:
        if member.voice and member.voice.channel:
            print(f"{member} is in {member.voice.channel} voice channel.")
            active_users[member.id] = member.name

    cursor.execute("SELECT user_id FROM VoiceActive")
    rows = cursor.fetchall()

    print("Removing any inactive sessions")
    for user in rows:
        if user[0] not in active_users.keys():
            update_time_stat(
                server,
                cursor,
                conn,
                user[0],
                heartbeat_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            remove_active_session(user[0], conn, cursor)
            print(
                f"User {server.get_member(user[0])} - {user[0]}: Removed from VoiceActive table."
            )

    print("Adding any new sessions")
    for user in active_users:
        if user not in [row[0] for row in rows]:
            add_active_session(server.get_member(user), cursor, conn)
            print(f"User {active_users[user]} - {user}: Added to VoiceActive table.")


# Remove user sessions that are no longer active
def remove_active_session(member, conn, cursor):
    cursor.execute(
        """
        DELETE FROM VoiceActive
        WHERE user_id = %s
        """,
        (member,),
    )
    conn.commit()


# Add new active user sessions
def add_active_session(member, cursor, conn):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{member} has joined {member.voice.channel} voice channel at {now}.")

    query = """INSERT INTO VoiceActive (user_id, channel_id, joined_time, last_heartbeat) 
                VALUES(%s, %s, %s, %s) ON DUPLICATE KEY UPDATE
                    channel_id = VALUES(channel_id),
                    last_heartbeat = VALUES(last_heartbeat);"""
    cursor.execute(query, (member.id, member.voice.channel.id, now, now))
    conn.commit()


def update_time_stat(server, cursor, conn, member, heartbeat_time=None):
    if heartbeat_time:
        left_time = heartbeat_time
    else:
        left_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # print(f"{member} has left {before.channel} voice channel at {left_time}.")
    query = """SELECT joined_time FROM VoiceActive WHERE user_id = %s;"""
    cursor.execute(query, (member,))
    result = cursor.fetchone()

    if result:
        joined_time = result[0]
        left_time = datetime.strptime(left_time, "%Y-%m-%d %H:%M:%S")
        time_in_voice = (left_time - joined_time).total_seconds()
        print(
            f"{server.get_member(member)} spent {time_in_voice} seconds in voice channel."
        )

        # Update the User's time in voice stats
        query = """INSERT INTO VoiceStats (user_id, date, time_seconds) 
               VALUES(%s, CURDATE(), %s) ON DUPLICATE KEY UPDATE
                time_seconds = time_seconds + VALUES(time_seconds);"""
        cursor.execute(query, (member, time_in_voice))
        conn.commit()

        xp = calculate_voice_xp(time_in_voice)
        print(xp)
        add_xp(member, xp, cursor, conn)

        # Delete the Active Voice session now that User disconnected
        cursor.execute(
            """
                DELETE FROM VoiceActive
                WHERE user_id = %s
            """,
            (member,),
        )

        conn.commit()
