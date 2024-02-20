import logging
import os
import asyncio
import threading
import colorlog

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from nakuru.entities.components import *

try:
    from util.plugin_dev.api.v1.config import *
    from util.plugin_dev.api.v1.message import AstrMessageEvent, MessageResult, message_handler, CommandResult
    from util.plugin_dev.api.v1.bot import GlobalObject
except ImportError:
    raise Exception("astrbot_plugin_telegram: 依赖导入失败。原因：请升级 AstrBot 到最新版本。")
from model.platform._nakuru_translation_layer import NakuruGuildMessage

log_colors_config = {
    'DEBUG': 'white',  # cyan white
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'cyan',
}

class Main:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.init_log()
        self.NAMESPACE = "astrbot_plugin_telegram"
        put_config(self.NAMESPACE, "是否启用 Telegram 平台", "telegram_enable", False, "是否启用 Telegram 平台")
        put_config(self.NAMESPACE, "telegram_token", "telegram_token", "", "Telegram Bot 的 Token")
        put_config(self.NAMESPACE, "start_message", "start_message", "I'm AstrBot, please talk to me!", "Telegram 的 /start 开始消息")
        self.cfg = load_config(self.NAMESPACE)
        self.start_message = self.cfg["start_message"]
        if self.cfg["telegram_enable"] and self.cfg["telegram_token"]:
            self.thread = threading.Thread(target=self.run_telegram_bot, args=(self.loop,)).start()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self.start_message)

    async def message_handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = NakuruGuildMessage()

        plain_text = update.message.text
        # check if it start with mention
        bot_username = context.bot.username
        logging.info(f"telegram/{update.effective_chat.id} -> {plain_text}")
        if f"@{bot_username}" not in plain_text:
            return
        message.user_id = update.effective_chat.id
        message.message = [Plain(plain_text),]
        result = await message_handler(
            message = message,
            platform = "telegram",
            session_id=update.effective_chat.id,
            role="member",
        )
        plain_text = ""
        image_path = None
        if isinstance(result.result_message, str):
            logging.info(f"telegram/{update.effective_chat.id} <- {result.result_message}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result.result_message)
            return
        for i in result.result_message:
            if isinstance(i, Plain):
                plain_text += i.text
            elif isinstance(i, Image):
                if i.path is not None:
                    image_path = i.path
                else:
                    image_path = i.file
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_path)
        if plain_text != "":
            await context.bot.send_message(chat_id=update.effective_chat.id, text=plain_text)
            
    def run_telegram_bot(self, loop: asyncio.AbstractEventLoop = None):
        asyncio.set_event_loop(loop)
        self.application = ApplicationBuilder().token(self.cfg['telegram_token']).build()
        start_handler = CommandHandler('start', self.start)
        message_handler = MessageHandler(filters.TEXT, self.message_handle)
        self.application.add_handler(start_handler)
        self.application.add_handler(message_handler)
        self.application.run_polling(stop_signals=None)

    def init_log(self):
        # logging config
        logging_level = logging.INFO
        if 'DEBUG' in os.environ and os.environ['DEBUG'] == 'true':
            logging_level = logging.DEBUG
        
        terminal_out = logging.StreamHandler()
        
        terminal_out.setFormatter(colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%m-%d %H:%M:%S",
            log_colors=log_colors_config,
        ))
        
        for t in logging.getLogger().handlers:
            logging.getLogger().removeHandler(t)
        
        logging.getLogger().addHandler(terminal_out)
        logging.getLogger().setLevel(logging_level)

    def run(self, ame: AstrMessageEvent):
        return CommandResult(
            hit=False,
            success=False,
            message_chain=[]
        )

    def info(self):
        return {
            "plugin_type": "platform",
            "name": "astrbot_plugin_telegram",
            "desc": "接入 Telegram 的插件",
            "help": "帮助信息查看：https://github.com/Soulter/astrbot_plugin_telegram",
            "version": "v1.0.0",
            "author": "Soulter",
            "repo": "https://github.com/Soulter/astrbot_plugin_telegram"
        }
