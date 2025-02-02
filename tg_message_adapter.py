import sys
import uuid
import asyncio

from astrbot.api.platform import Platform, AstrBotMessage, MessageMember, PlatformMetadata, MessageType
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Plain, Image, Record
from astrbot.core.platform.astr_message_event import MessageSesion
from astrbot.api.platform import register_platform_adapter
from astrbot.core import logger

from telegram import Update, File
from telegram.ext import ApplicationBuilder, ContextTypes, filters
from telegram.constants import ChatType
from telegram.ext import MessageHandler as TelegramMessageHandler
from .tg_message_event import TelegramPlatformEvent

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

@register_platform_adapter("telegram", "telegram 适配器", default_config_tmpl={
    "telegram_token": "your_token",
    "start_message": "Hello, I'm AstrBot!",
    "telegram_api_base_url": "https://api.telegram.org/bot",  # 新增配置项
    "提示": "由于 Telegram 无法在中国大陆 / Iran 访问，如果你的网络环境为中国大陆 / Iran，记得在 `其他配置` 处设置代理！"
})
class TelegramPlatformAdapter(Platform):

    def __init__(self, platform_config: dict, platform_settings: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(event_queue)
        self.config = platform_config
        self.settingss = platform_settings
        self.client_self_id = uuid.uuid4().hex[:8]
        self.message_queue = asyncio.Queue()  # 新增消息队列
        self.rate_limit = 30  # 新增速率限制，每用户每 30 秒处理一次
        self.user_last_processed_time = {}  # 新增用户最后处理时间记录

    @override
    async def send_by_session(self, session: MessageSesion, message_chain: MessageChain):
        from_username = session.session_id
        await TelegramPlatformEvent.send_with_client(self.client, message_chain, from_username)
        await super().send_by_session(session, message_chain)

    @override
    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            "telegram",
            "telegram 适配器",
        )

    @override
    async def run(self):
        base_url = self.config.get("telegram_api_base_url", "https://api.telegram.org/bot")
        if not base_url:
            base_url = "https://api.telegram.org/bot"
        
        self.application = ApplicationBuilder().token(self.config['telegram_token']).base_url(base_url).build()
        message_handler = TelegramMessageHandler(
            filters=filters.ALL,  # 允许接收所有类型的消息
            callback=self.enqueue_message  # 修改为 enqueue_message
        )
        self.application.add_handler(message_handler)
        await self.application.initialize()
        await self.application.start()
        queue = self.application.updater.start_polling()
        self.client = self.application.bot
        print("Telegram Platform Adapter is running.")

        asyncio.create_task(self.process_message_queue())  # 新增消息队列处理任务

        await queue

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self.config["start_message"])

    async def enqueue_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """将消息放入队列"""
        await self.message_queue.put((update, context))

    async def process_message_queue(self):
        """处理消息队列中的消息"""
        while True:
            update, context = await self.message_queue.get()
            user_id = str(update.effective_user.id)

            current_time = asyncio.get_event_loop().time()
            last_processed_time = self.user_last_processed_time.get(user_id, 0)

            if current_time - last_processed_time >= self.rate_limit:
                await self.convert_message(update, context)
                self.user_last_processed_time[user_id] = current_time
                # 处理完消息后，短暂休眠，避免 CPU 占用过高
                await asyncio.sleep(0.01)
            else:
                # 将消息重新放回队列
                await self.message_queue.put((update, context))
                # 短暂休眠，避免 CPU 占用过高
                await asyncio.sleep(0.01)

    async def convert_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = AstrBotMessage()
        if update.effective_chat.type == ChatType.PRIVATE:
            message.type = MessageType.FRIEND_MESSAGE
        else:
            message.type = MessageType.GROUP_MESSAGE
            message.group_id = update.effective_chat.id
        message.message_id = str(update.message.message_id)
        message.session_id = str(update.effective_chat.id)
        message.sender = MessageMember(str(update.effective_user.id), update.effective_user.username)
        message.self_id = str(context.bot.id)
        message.raw_message = update
        message.message_str = ""

        if update.message.text:
            plain_text = update.message.text
            message.message = [Plain(plain_text),]
            message.message_str = plain_text
            await self.handle_msg(message)
        elif update.message.voice:
            file = await update.message.voice.get_file()
            message.message = [Record(file=file.file_path, url=file.file_path),]
            message.message_str = f"[语音消息: {file.file_path}]"
            await self.handle_msg(message)
        else:
            message.message = []
            logger.info(f"收到不支持的消息类型，来自：{message.sender.user_id if message.sender else '未知'}，已忽略")

    async def handle_msg(self, message: AstrBotMessage):
        message_event = TelegramPlatformEvent(
            message_str=message.message_str,
            message_obj=message,
            platform_meta=self.meta(),
            session_id=message.session_id,
            client=self.client
        )
        self.commit_event(message_event)
