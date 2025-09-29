"""Async Telegram bot implementation using Telethon."""

from __future__ import annotations

import asyncio

from telethon import TelegramClient, events

from xbot.config.settings import Settings, get_settings
from xbot.services.operator import CommandContext, CommandProcessor


class TelegramOperatorBot:
    """Thin wrapper around Telethon to expose the command processor."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        context: CommandContext,
    ) -> None:
        self._settings = settings or get_settings()
        self._context = context
        self._processor = CommandProcessor(context)
        self._client = TelegramClient(
            "xbot",
            self._settings.telegram.api_id,
            self._settings.telegram.api_hash,
        )

    async def run(self) -> None:
        if not self._settings.telegram.bot_token:
            raise RuntimeError("Telegram bot token is not configured")

        await self._client.start(bot_token=self._settings.telegram.bot_token)

        @self._client.on(events.NewMessage(from_users=[self._settings.telegram.operator_chat_id]))
        async def handler(event: events.NewMessage.Event) -> None:
            response = self._processor.handle(event.raw_text or "")
            await event.respond(response)

        await self._client.run_until_disconnected()

    def run_blocking(self) -> None:
        asyncio.run(self.run())


__all__ = ["TelegramOperatorBot"]
