CREATE DATABASE IF NOT EXISTS discord_bot_db;
USE discord_bot_db;

CREATE TABLE Users (
    user_id BIGINT PRIMARY KEY NOT NULL,
    username VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    joined_date  DATETIME,
    xp BIGINT DEFAULT 0,
    level INT DEFAULT 1,
    messages_sent BIGINT DEFAULT 0
);

CREATE TABLE VoiceActive (
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    joined_time DATETIME NOT NULL,
    last_heartbeat DATETIME NOT NULL,
    PRIMARY KEY (user_id)
);
CREATE TABLE VoiceStats (
    user_id BIGINT NOT NULL,
    date DATE NOT NULL,
    time_seconds BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date),
    INDEX idx_date (date)
);