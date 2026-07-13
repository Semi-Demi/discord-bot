#!/bin/sh
set -e

# Only run setup if it hasn't been done yet.
if [ ! -f /data/config/config.json ]; then
    printf "$BOT_NAME\n\ny\n\n" | redbot-setup
fi

exec redbot "$BOT_NAME" --token "$DISCORD_TOKEN" --prefix "$PREFIX"