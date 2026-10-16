#!/bin/sh
set -e

# Only run setup if it hasn't been done yet.
if ! redbot --list-instances | grep -Fxq "$BOT_NAME"; then
    echo "No RedBot setup found!"
    echo "\nStarting redbot setup ..."
    redbot-setup --no-prompt --instance-name "$BOT_NAME" --data-path /data
fi

exec redbot "$BOT_NAME" --token "$DISCORD_TOKEN" --prefix "$PREFIX"
