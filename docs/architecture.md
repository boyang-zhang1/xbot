# Architecture Overview

## Context
The toolkit ingests content from monitored X accounts, enriches it with machine translation, and republishes curated threads. Operators manage the pipeline through a CLI or Telegram bot while the system keeps artefacts persisted on disk (pluggable storage layer).

## Logical Components
1. **Configuration** - `xbot.config.settings` loads typed settings from environment variables, `.env`, and default values.
2. **Models** - Pydantic models describe tweets, threads, media assets, translation artefacts, and operator tasks.
3. **Storage Layer** - `interfaces.storage` exposes repositories for tweets, translations, jobs, and metadata with a JSON-backed implementation (`infra.repositories.json_store`).
4. **X Client** - `infra.clients.x_publisher` and `infra.clients.x_scraper` wrap the Tweepy/Tweety SDKs for publishing and ingestion with credential rotation and rate-limit guards.
5. **Translation Client** - `infra.clients.openai` orchestrates OpenAI calls with retry/backoff, context budgeting, and manual override helpers.
6. **Services** - Business logic for scraping, translation, publishing, scheduling, operator review, and Telegram command orchestration.
7. **Presentation Layer** - CLI via Typer (`cli.main`) with migrate/scrape/translate/publish/review/schedule modules, plus Telegram bot handlers (`infra.telegram.bot`).

## Data Flow
1. **Scrape** - Scheduler triggers `ScraperService` which pulls latest tweets per watchlist entry, normalises payloads, and stores results.
2. **Translate** - `TranslationService` converts tweet threads to Simplified Chinese, persists translations, and stores manual prompts.
3. **Publish** - `PublisherService` posts translated content to X, handling media uploads and templated acknowledgements.
4. **Operate** - Telegram bot and review CLI expose commands for full pipeline control, while the scheduler coordinates deferred execution.

## Extensibility
- Storage adapters can be swapped by implementing repository interfaces.
- Translation backends are pluggable by conforming to `TranslationProvider` protocol.
- Scheduler supports long-running worker via APScheduler or Celery in future iterations.

## Non-Goals
- Full X automation resilience (captcha solving, advanced ban evasion) is intentionally out of scope.
- Secrets management beyond `.env` is deferred to hosting environment (use Vault/Secret Manager in production).
