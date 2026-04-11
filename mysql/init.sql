CREATE DATABASE IF NOT EXISTS discord_bot_db;
USE discord_bot_db;

CREATE TABLE Users (
    user_id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    joined_date  DATETIME,
    xp INT DEFAULT 0
);