# All-Telegram-Bots

## Current Bots

This monorepo runs the following bots as concurrent tasks in a single Fly.io machine:

| Bot | Folder | Token Env Var |
|---|---|---|
| Film Bot | `film_bot/` | `FILM_BOT_TOKEN` |
| Got Water Bot | `gotwaterbot/` | `GOTWATER_BOT_TOKEN` |
| Unit Converter Bot | `unitconverterbot/` | `UC_BOT_TOKEN` |
| WSH Nationals Bot | `wshnationalsbot/` | `WSHNATS_BOT_TOKEN` |
| Uno Bot | `unobot/` | `UNO_BOT_TOKEN` (optional) |
| XO Game Bot | `xogamebot/` | `XO_BOT_TOKEN` (optional) |
| Blackjack Bot | `blackjackbot/` | `BLACKJACK_BOT_TOKEN` (optional) |

> **Austin 311 Bot has been fully removed from this repo.** It now lives entirely in `seanatwork/austin311bot-unofficial` (GitHub Pages + code) and will get its own Fly.io deployment later.

## Fly.io Deployment

- **App name**: `all-telegram-bots`
- **Machine**: 1x `shared-cpu-1x:512MB` in `iad` region
- **Entrypoint**: `python main.py`
- **Primary region**: `dfw`
- **Deploy strategy**: immediate

### Current Secrets
- `CHAT_ID`
- `FILM_BOT_TOKEN`
- `GOOGLE_MAPS_API_KEY`
- `GOTWATER_BOT_TOKEN`
- `LINEUP_CHANNEL_ID`
- `TMDB_API_KEY`
- `UC_BOT_TOKEN`
- `WSHNATS_BOT_TOKEN`
- `UNO_BOT_TOKEN`
- `XO_BOT_TOKEN`
- `BLACKJACK_BOT_TOKEN`

## Uno Bot (`unobot/`)

Integrated from [mau_mau_bot](https://github.com/jh0ker/mau_mau_bot). Ported from PTB v13 (sync) to PTB v21 (async) so it shares the same environment as all other bots. Skipped automatically if `UNO_BOT_TOKEN` is unset.

- DB: `/data/uno.sqlite3` (set via `UNO_DB` env var — defaulted in `shared_vars.py`)
- Token: read from `UNO_BOT_TOKEN` secret directly in `bot.py:build_app()`
- `pony==0.7.19` is its only extra dependency (in `unobot/requirements.txt`, installed at build time)
- To deploy after setting the token: `fly secrets set UNO_BOT_TOKEN=<token> --app all-telegram-bots && fly deploy --app all-telegram-bots`

## XO Game Bot (`xogamebot/`)

Tic-tac-toe over inline mode, ported from [reza00farjam/XO-Game-Bot](https://github.com/reza00farjam/XO-Game-Bot). Original used Pyrogram (MTProto); port uses PTB v21 like all other bots — no `API_ID`/`API_HASH` needed. Skipped automatically if `XO_BOT_TOKEN` is unset.

- Token: read from `XO_BOT_TOKEN` secret directly in `bot.py:build_app()`
- Inline mode must be enabled in BotFather (`/setinline`)
- Game state is in-memory only (capped at 100 games via LRU); games disappear on restart
- No extra dependencies
