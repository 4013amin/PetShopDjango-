from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
import logging
from .models import ChatMessage, OTP

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sender = self.scope['url_route']['kwargs']['sender']
        self.receiver = self.scope['url_route']['kwargs']['receiver']
        sorted_users = sorted([self.sender, self.receiver])
        self.room_group_name = f"chat_{sorted_users[0]}_{sorted_users[1]}"

        logger.info(f"WebSocket connecting: {self.scope['path']}")
        logger.info(f"Sender: {self.sender}, Receiver: {self.receiver}")

        # Add to group and accept connection
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Fetch messages with related sender, receiver, and reply_to
        messages = await sync_to_async(
            lambda: list(ChatMessage.objects.filter(
                sender__phone__in=[self.sender, self.receiver],
                receiver__phone__in=[self.sender, self.receiver]
            ).select_related('sender', 'receiver', 'reply_to'))
        )()

        # Send existing messages
        for msg in messages:
            reply_to_data = None
            if msg.reply_to:
                reply_to_data = {
                    'message': msg.reply_to.message,
                    'sender': msg.reply_to.sender.phone,
                    'timestamp': msg.reply_to.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
            await self.send(text_data=json.dumps({
                'message': msg.message,
                'sender': msg.sender.phone,
                'receiver': msg.receiver.phone,
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'reply_to': reply_to_data  # اطلاعات پیام مرجع
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected: {self.room_group_name}")

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_phone = text_data_json['sender']
        receiver_phone = text_data_json['receiver']
        reply_to_message = text_data_json.get('reply_to')  # پیام مرجع (اختیاری)

        # Fetch sender and receiver users
        sender_user = await sync_to_async(
            lambda: OTP.objects.filter(phone=sender_phone).first()
        )()
        receiver_user = await sync_to_async(
            lambda: OTP.objects.filter(phone=receiver_phone).first()
        )()

        if not sender_user or not receiver_user:
            logger.error(f"Sender or receiver does not exist. Sender: {sender_phone}, Receiver: {receiver_phone}")
            await self.send(text_data=json.dumps({
                'error': 'Sender or receiver does not exist.'
            }))
            return

        # Find the message being replied to (if any)
        reply_to = None
        if reply_to_message:
            reply_to = await sync_to_async(
                lambda: ChatMessage.objects.filter(
                    sender__phone__in=[self.sender, self.receiver],
                    receiver__phone__in=[self.sender, self.receiver],
                    message=reply_to_message
                ).first()
            )()

        # Save the new message
        chat_message = await sync_to_async(
            lambda: ChatMessage.objects.create(
                sender=sender_user,
                receiver=receiver_user,
                message=message,
                reply_to=reply_to
            )
        )()

        # Prepare reply_to data for sending
        reply_to_data = None
        if chat_message.reply_to:
            reply_to_data = {
                'message': chat_message.reply_to.message,
                'sender': chat_message.reply_to.sender.phone,
                'timestamp': chat_message.reply_to.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }

        # Broadcast the message to the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': chat_message.message,
                'sender': sender_phone,
                'receiver': receiver_phone,
                'timestamp': chat_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'reply_to': reply_to_data
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'receiver': event['receiver'],
            'timestamp': event['timestamp'],
            'reply_to': event['reply_to']
        }))