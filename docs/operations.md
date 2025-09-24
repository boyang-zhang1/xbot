# Operations Guide

## Prerequisites
- Python 3.11+
- Twitter API credentials (consumer key/secret, per-account tokens)
- Telegram bot token, API ID, and hash
- OpenAI API key

## Configuration
1. Create a `.env` file in the repository root.
2. Populate required keys:
   ```dotenv
   TWITTER_SCRAPER_HANDLES=account_one,account_two
   TWITTER_CONSUMER_KEYS=...
   TWITTER_CONSUMER_SECRETS=...
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_API_ID=...
   TELEGRAM_API_HASH=...
   OPENAI_API_KEY=...
   ```
3. Optional values (with defaults) are documented in `twitter_bot/config/settings.py` docstrings.

## Common Tasks
- **Initial migration**
  ```bash
  poetry run twitter-bot migrate from-legacy --source twitter_bot-main
  ```
- **Scrape all watched accounts**
  ```bash
  poetry run twitter-bot scrape all
  ```
- **Translate a tweet/thread**
  ```bash
  poetry run twitter-bot translate tweet --tweet-id 1234567890
  ```
- **Publish translated thread**
  ```bash
  poetry run twitter-bot publish tweet --tweet-id 1234567890 --profile default
  ```
- **Queue jobs for later execution**
  ```bash
  poetry run twitter-bot schedule enqueue-translate 1234567890 --run-at "2024-07-21T14:00:00Z"
  poetry run twitter-bot schedule run
  ```
- **Review stored translations**
  ```bash
  poetry run twitter-bot review translations
  poetry run twitter-bot review show 1234567890
  poetry run twitter-bot review export 1234567890 exports/1234567890.txt
  ```
- **Run the Telegram bot**
  ```bash
  poetry run twitter-bot telegram run
  ```

## File Layout
- `var/data/` - persisted tweets and translations (JSON by default)
- `var/logs/` - structured logs from services and bots
- `var/tmp/` - download cache for media assets

## Backups
- Schedule regular copies of `var/data/` and job states.
- Use `twitter-bot review export` to extract individual translations for archival sharing.

## Troubleshooting
- **Translation failures** - inspect `var/logs/translation.log` and re-run with `--manual` to obtain prompt.
- **Publish errors** - run in `--dry-run` to validate length and assets without posting.
- **Telegram connectivity** - confirm session file in `var/telegram/` and regenerate if expired using CLI `telegram auth` flow.
- **Missing optional dependencies** - when running in air-gapped environments, install `tweety`, `tweepy`, `httpx`, and `requests-oauthlib` to enable scraping/publishing, otherwise the CLI will raise a runtime error when those features are exercised.
