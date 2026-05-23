# Marathon Support Bot

A Discord ticket bot. Users open support tickets via a button — each ticket becomes a private channel visible only to the user, moderators, and the bot. Includes full open/close flow with audit logging.

## Features

- `/ticket_panel` — posts a button to any channel; users click it to open a ticket
- Each ticket is a private channel with proper permission overwrites
- Ticket creator or any moderator can close tickets
- All actions (open, close) are logged to a designated log channel
- Stores the opener's ID in the channel topic for reliable tracking

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables:

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Your bot token |
| `MOD_ROLE_IDS` | Comma-separated moderator role IDs |
| `TICKET_CATEGORY_ID` | Category where ticket channels are created |
| `TICKET_LOG_CHANNEL_ID` | Channel to log ticket events |
| `TICKET_BANNER_URL` | Optional banner image for the ticket embed |

## Run

```bash
python bot.py
```

Or with Docker:

```bash
docker build -t marathon-support .
docker run --env-file .env marathon-support
```

Deployed on [Fly.io](https://fly.io).

## Stack

- Python
- discord.py
- Docker / Fly.io
