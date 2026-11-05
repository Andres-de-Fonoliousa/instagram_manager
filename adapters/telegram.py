import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

log = logging.getLogger("tg")


class TelegramPoster:
    def __init__(self, bot: Bot, channel: str):
        self.bot = bot
        self.channel = channel

    async def apost(self, image_path: str, caption: str) -> str:
        message = await self.bot.send_photo(
            chat_id=self.channel,
            photo=FSInputFile(Path(image_path)),
            caption=caption,
            disable_notification=True,
        )
        if self.channel.startswith("@"):
            return f"https://t.me/{self.channel[1:]}/{message.message_id}"
        return f"posted to channel {self.channel} (msg {message.message_id})"