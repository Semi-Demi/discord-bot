XP_RATE_VOICE = 100  # XP per minute of voice activity
XP_RATE_CHAT = 50  # XP per message sent
MAX_LEVEL = 80
MAX_PRESTIGE = 10
XP_INCREASE_RATE = 0.1
XP_PER_LEVEL = 1.15


def calculate_voice_xp(seconds):
    return int(seconds // 10) * XP_RATE_VOICE


def calculate_chat_xp():
    return XP_RATE_CHAT


def xp_needed(level, prestige):
    return int((level / XP_INCREASE_RATE) ** XP_PER_LEVEL) * (1 + prestige * 0.10)


def calculate_total_xp():
    total_xp = 0
    for p in range(MAX_PRESTIGE + 1):
        print(f"\nCalculating XP for prestige {p}...")
        for l in range(1, MAX_LEVEL + 1):
            total_xp += xp_needed(l, p)
            print(f"Level {l} requires {xp_needed(l, p)} XP")
    print(f"\nTotal XP needed for all levels and prestiges: {total_xp}")


def add_xp(user_id, xp, cursor, conn):
    query = """SELECT user_level, prestige, xp FROM Users WHERE user_id = %s;"""
    cursor.execute(query, (user_id,))
    level, prestige, current_xp = cursor.fetchone()

    levelup, prestigeup = False, False

    xp_required = xp_needed(level, prestige)
    print("required xp", xp_required)
    print("xp added", xp + current_xp)
    if xp + current_xp >= xp_required:
        level += 1
        levelup = True
        xp = 0
    else:
        xp += current_xp

    if level > MAX_LEVEL:
        if prestige < MAX_PRESTIGE:
            prestige += 1
            level = 1
            xp = 0
            prestigeup = True
        else:
            level = MAX_LEVEL
            levelup = False
            xp = 0

    query = """UPDATE Users SET xp = %s, user_level = %s, prestige = %s WHERE user_id = %s"""
    cursor.execute(query, (xp, level, prestige, user_id))
    conn.commit()

    return levelup, prestigeup
