XP_RATE_VOICE = 100  # XP per minute of voice activity
XP_RATE_CHAT = 50  # XP per message sent


def calculate_voice_xp(seconds):
    return int(seconds // 60) * XP_RATE_VOICE


def calculate_chat_xp():
    return XP_RATE_CHAT


def add_xp(user_id, xp, cursor, conn):
    query = "UPDATE Users SET xp = xp + %s WHERE user_id = %s"
    cursor.execute(query, (xp, user_id))
    conn.commit()
