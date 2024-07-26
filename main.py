import logging
import asyncio
import threading

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters
from telegram.ext import MessageHandler as TelegramMessageHandler
try:
    from util.plugin_dev.api.v1.config import *
    from util.plugin_dev.api.v1.message import *
    from util.plugin_dev.api.v1.bot import Context
    from util.plugin_dev.api.v1.types import Plain, Image
    from util.plugin_dev.api.v1.register import register_platform
except ImportError:
    raise Exception("astrbot_plugin_telegram: 依赖导入失败。原因：请升级 AstrBot 到最新版本。")

class Main:
    def __init__(self, context: Context) -> None:
        self.NAMESPACE = "astrbot_plugin_telegram"
        put_config(self.NAMESPACE, "是否启用 Telegram 平台", "telegram_enable", False, "是否启用 Telegram 平台")
        put_config(self.NAMESPACE, "telegram_token", "telegram_token", "", "Telegram Bot 的 Token")
        put_config(self.NAMESPACE, "start_message", "start_message", "I'm AstrBot, please talk to me!", "Telegram 的 /start 开始消息")
        self.cfg = load_config(self.NAMESPACE)
        self.start_message = self.cfg["start_message"]
        self.logger = logging.getLogger("astrbot")
        # get the message handler in astrbot
        self.message_handler = context.message_handler
        self.context = context
        assert isinstance(self.message_handler, MessageHandler)
        
        register_platform(self.NAMESPACE, context, None)
        
        if self.cfg["telegram_enable"] and self.cfg["telegram_token"]:
            self.context.register_task(self.run_telegram_bot(), "telegram_bot")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self.start_message)

    async def message_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = AstrBotMessage()

        plain_text = update.message.text
        self.logger.info(f"telegram/{update.effective_chat.id} -> {plain_text}")
        message.message_id = str(update.message.message_id)
        message.message_str = plain_text
        message.sender = MessageMember(str(update.effective_chat.id), update.effective_chat.effective_name)
        message.message = [Plain(plain_text),]
        message.self_id = str(context.bot.id)
        
        ame = AstrMessageEvent.from_astrbot_message(
            message=message,
            context=self.context,
            platform_name="astrbot_plugin_telegram",
            session_id=str(update.effective_chat.id),
            role="member"
        )
        message_result = await self.message_handler.handle(message=ame)
        assert isinstance(message_result, MessageResult)
        
        plain_text = ""
        image_path = None
        if isinstance(message_result.result_message, str):
            self.logger.info(f"telegram/{update.effective_chat.id} <- {message_result.result_message}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message_result.result_message)
            return
        for i in message_result.result_message:
            if isinstance(i, Plain):
                plain_text += i.text
            elif isinstance(i, Image):
                if i.path:
                    image_path = i.path
                else:
                    image_path = i.file
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_path)
        if plain_text:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=plain_text)
            
            
    async def run_telegram_bot(self):
        self.application = ApplicationBuilder().token(self.cfg['telegram_token']).build()
        message_handler = TelegramMessageHandler(filters.TEXT, self.message_handle)
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(message_handler)
        await self.application.initialize()
        await self.application.start()
        queue = self.application.updater.start_polling()
        await queue