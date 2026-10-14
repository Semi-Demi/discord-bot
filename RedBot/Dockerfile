FROM python:3.11

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    openjdk-17-jre-headless \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install -U pip wheel \
    && python -m pip install -U Red-DiscordBot

RUN mkdir -p /data

COPY RedBot/entry.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN useradd -m redbot

USER redbot

VOLUME ["/data"]

WORKDIR /data

ENTRYPOINT ["/entrypoint.sh"]
