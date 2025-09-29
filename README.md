# XBot Toolkit

A production-grade toolkit that monitors curated X accounts, translates their long-form threads into polished Simplified Chinese, and republishes translations through X and a Telegram operator bot.

## Features
- Account watchlists with incremental scraping and credential rotation (Tweety-powered client)
- Translation pipeline with OpenAI integration, retry/backoff, and manual override workflows
- X publishing with thread support, media handling, templated closing messages, and duplicate safeguards
- Telegram control bot plus review CLI for operators to inspect, export, and queue work
- Lightweight scheduler with JSON-backed job store for scrape/translate/publish automation
- Structured logging, typed configuration, and CI-ready tooling for automated quality gates

## Quick Start
1. **Create a virtual environment** using Poetry or your preferred tool, then install dependencies:
   ```bash
   poetry install
   ```
2. **Configure secrets** by creating a `.env` file and populating the environment variables described in `docs/operations.md`.
3. **Run migrations** to bring legacy JSON exports into the new storage layout:
   ```bash
   poetry run xbot migrate from-legacy --source legacy_data_dump
   ```
4. **Scrape, translate, schedule, review, and publish** via the CLI or Telegram bot.

See `docs/operations.md` for full instructions and runbooks.

## Repository Layout
- `src/xbot/` - Source package with services, models, and interfaces
- `tests/` - Unit and integration test suites
- `scripts/` - Utility scripts (migrations, data seeding)
- `docs/` - Architecture and operations documentation
- `var/` - Runtime artefacts (JSON stores, logs), ignored by git

## Status
This repository is under active development as we rebuild the legacy automation stack into a sustainable open-source project.
