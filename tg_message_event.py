from astrbot.api.event import AstrMessageEvent, MessageChain
from astrbot.api.platform import AstrBotMessage, PlatformMetadata
from astrbot.api.message_components import Plain, Image
from telegram.ext import ExtBot

class TelegramPlatformEvent(AstrMessageEvent):
    def __init__(self, message_str: str, message_obj: AstrBotMessage, platform_meta: PlatformMetadata, session_id: str, client: ExtBot):
        super().__init__(message_str, message_obj, platform_meta, session_id)
        self.client = client
        
    @staticmethod
    async def send_with_client(client: ExtBot, message: MessageChain, user_name: str):
        plain_text = ""
        image_path = None
        for i in message.chain:
            if isinstance(i, Plain):
                if message.is_split_:
                    await client.send_message(chat_id=user_name, text=i.text)
                plain_text += i.text
            elif isinstance(i, Image):
                if i.path:
                    image_path = i.path
                else:
                    image_path = i.file
                await client.send_photo(chat_id=user_name, photo=image_path)
        if plain_text:
            await client.send_message(chat_id=user_name, text=plain_text)
                
        
    async def send(self, message: MessageChain):
        await self.send_with_client(self.client, message, self.get_sender_id())
        await super().send(message)