# Operations Guide

## Overview
This guide covers setup, configuration, and daily operations for the XBot Toolkit (v1.0). All features are production-ready with CI-validated quality gates.

## Prerequisites
- Python 3.11+
- Poetry for dependency management
- X API credentials (consumer key/secret, per-account tokens)
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
3. Optional values (with defaults) are documented in `xbot/config/settings.py` docstrings.

## Common Tasks
- **Initial migration**
  ```bash
  poetry run xbot migrate from-legacy --source legacy_data_dump
  ```
- **Scrape all watched accounts**
  ```bash
  poetry run xbot scrape all
  ```
- **Translate a tweet/thread**
  ```bash
  poetry run xbot translate tweet --tweet-id 1234567890
  ```
- **Publish translated thread**
  ```bash
  poetry run xbot publish tweet --tweet-id 1234567890 --profile default
  ```
- **Queue jobs for later execution**
  ```bash
  poetry run xbot schedule enqueue-translate 1234567890 --run-at "2024-07-21T14:00:00Z"
  poetry run xbot schedule run
  ```
- **Review stored translations**
  ```bash
  poetry run xbot review translations
  poetry run xbot review show 1234567890
  poetry run xbot review export 1234567890 exports/1234567890.txt
  ```
- **Run the Telegram bot**
  ```bash
  poetry run xbot telegram run
  ```

## File Layout
- `var/data/` - persisted tweets and translations (JSON by default)
- `var/logs/` - structured logs from services and bots
- `var/tmp/` - download cache for media assets

## Backups
- Schedule regular copies of `var/data/` and job states.
- Use `xbot review export` to extract individual translations for archival sharing.

## Continuous Integration
The project includes automated CI workflows (`.github/workflows/ci.yml`) that run on every push:
- Code quality checks (ruff linting)
- Type checking (mypy with strict mode)
- Full test suite execution
- Dependency validation

All tests must pass before merging to the main branch.

## Troubleshooting
- **Translation failures** - inspect `var/logs/translation.log` and re-run with `--manual` to obtain prompt.
- **Publish errors** - run in `--dry-run` to validate length and assets without posting.
- **Telegram connectivity** - confirm session file in `var/telegram/` and regenerate if expired using CLI `telegram auth` flow.
- **Missing optional dependencies** - when running in air-gapped environments, install `tweety`, `tweepy`, `httpx`, and `requests-oauthlib` to enable scraping/publishing, otherwise the CLI will raise a runtime error when those features are exercised.
