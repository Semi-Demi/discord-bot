FROM python:3.13

WORKDIR /app/discord-bot

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.9.2 /uv /bin/

RUN uv sync

COPY python/time_tracking.py time_tracking.py
COPY python/user_xp.py user_xp.py
COPY python/main.py main.py

RUN useradd -m pythonbot

RUN chown -R pythonbot:pythonbot /app/discord-bot

USER pythonbot

CMD ["uv", "run", "main.py"]
