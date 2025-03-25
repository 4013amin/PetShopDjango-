from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
import logging
from .models import ChatMessage, OTP

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # دریافت فرستنده و گیرنده از URL
        self.sender = self.scope['url_route']['kwargs']['sender']
        self.receiver = self.scope['url_route']['kwargs']['receiver']
        sorted_users = sorted([self.sender, self.receiver])
        self.room_group_name = f"chat_{sorted_users[0]}_{sorted_users[1]}"

        logger.info(f"WebSocket connecting: {self.scope['path']}")
        logger.info(f"Sender: {self.sender}, Receiver: {self.receiver}")

        # اضافه کردن کانکشن به گروه
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # ارسال پیام‌های قبلی (اختیاری)
        messages = await sync_to_async(ChatMessage.objects.filter)(
            sender_id__in=[self.sender, self.receiver],
            receiver_id__in=[self.sender, self.receiver]
        )
        for msg in await sync_to_async(list)(messages):
            await self.send(text_data=json.dumps({
                'message': msg.message,
                'sender': msg.sender.phone,
                'receiver': msg.receiver.phone
            }))

    async def disconnect(self, close_code):
        # حذف کانکشن از گروه
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected: {self.room_group_name}")

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")  # دیباگ
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender = text_data_json['sender']
        receiver = text_data_json['receiver']

        # بررسی وجود فرستنده و گیرنده در مدل OTP
        sender_user_exists = await sync_to_async(OTP.objects.filter(id=sender).exists)()
        receiver_user_exists = await sync_to_async(OTP.objects.filter(id=receiver).exists)()

        if not sender_user_exists or not receiver_user_exists:
            logger.error(f"Sender or receiver does not exist. Sender: {sender}, Receiver: {receiver}")
            await self.send(text_data=json.dumps({
                'error': 'Sender or receiver does not exist.'
            }))
            return

        # ذخیره پیام در پایگاه داده
        await sync_to_async(ChatMessage.objects.create)(
            sender_id=sender,
            receiver_id=receiver,
            message=message
        )

        # ارسال پیام به گروه
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender,
                'receiver': receiver
            }
        )

    async def chat_message(self, event):
        # ارسال پیام به WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'receiver': event['receiver']
        }))