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
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        messages = await sync_to_async(
            lambda: list(ChatMessage.objects.filter(
                sender__phone__in=[self.sender, self.receiver],
                receiver__phone__in=[self.sender, self.receiver]
            ).select_related('sender', 'receiver', 'reply_to', 'reply_to__sender'))
        )()

        for msg in messages:
            if self.receiver == msg.receiver.phone and msg.status != 'SEEN':
                msg.status = 'SEEN'
                await sync_to_async(msg.save)()

            reply_to_data = None
            if msg.reply_to:
                reply_to_data = {
                    'id': msg.reply_to.id,
                    'message': msg.reply_to.message,
                    'sender': msg.reply_to.sender.phone if msg.reply_to.sender else None,
                    'timestamp': msg.reply_to.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }

            message_data = {
                'id': msg.id,
                'message': msg.message,
                'sender': msg.sender.phone,
                'receiver': msg.receiver.phone,
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'status': msg.status,
                'reply_to': reply_to_data
            }
            await self.send(text_data=json.dumps(message_data))

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'id': msg.id,
                    'message': msg.message,
                    'sender': msg.sender.phone,
                    'receiver': msg.receiver.phone,
                    'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': msg.status,
                    'reply_to': reply_to_data
                }
            )
            

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected: {self.room_group_name}")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        action = text_data_json.get('action')
        
        if action == 'delete_chat':
            sender_phone = text_data_json['sender']
            receiver_phone = text_data_json['receiver']
            
            await sync_to_async(ChatMessage.objects.filter(
                sender__phone=sender_phone,
                receiver__phone=receiver_phone
            ).delete)()
            await sync_to_async(ChatMessage.objects.filter(
                sender__phone=receiver_phone,
                receiver__phone=sender_phone
            ).delete)()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_deleted',
                    'sender': sender_phone,
                    'receiver': receiver_phone
                }
            )
            return

        message = text_data_json['message']
        sender_phone = text_data_json['sender']
        receiver_phone = text_data_json['receiver']
        status = text_data_json.get('status', 'SENT')
        reply_to_id = text_data_json.get('reply_to_id')

        sender_user = await sync_to_async(
            lambda: OTP.objects.filter(phone=sender_phone).first()
        )()
        receiver_user = await sync_to_async(
            lambda: OTP.objects.filter(phone=receiver_phone).first()
        )()

        if not sender_user or not receiver_user:
            await self.send(text_data=json.dumps({'error': 'Sender or receiver does not exist.'}))
            return

        reply_to = None
        if reply_to_id:
            reply_to = await sync_to_async(
                lambda: ChatMessage.objects.filter(id=reply_to_id).select_related('sender').first()
            )()

        chat_message = await sync_to_async(
            lambda: ChatMessage.objects.create(
                sender=sender_user,
                receiver=receiver_user,
                message=message,
                status=status,
                reply_to=reply_to
            )
        )()

        chat_message = await sync_to_async(
            lambda: ChatMessage.objects.select_related('sender', 'receiver', 'reply_to', 'reply_to__sender').get(id=chat_message.id)
        )()

        reply_to_data = None
        if chat_message.reply_to:
            reply_to_data = {
                'id': chat_message.reply_to.id,
                'message': chat_message.reply_to.message,
                'sender': chat_message.reply_to.sender.phone if chat_message.reply_to.sender else None,
                'timestamp': chat_message.reply_to.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': chat_message.id,
                'message': chat_message.message,
                'sender': sender_phone,
                'receiver': receiver_phone,
                'timestamp': chat_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'status': chat_message.status,
                'reply_to': reply_to_data
            }
        )
        
        if self.receive == receiver_phone :
            await self.send(text_data= json.dump({
                'type' : 'notification',
                'title': 'پیام جدید',
                'body': f"پیام جدید از {sender_phone}: {message}"
            }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'message': event['message'],
            'sender': event['sender'],
            'receiver': event['receiver'],
            'timestamp': event['timestamp'],
            'status': event['status'],
            'reply_to': event['reply_to']
        }))

    async def chat_deleted(self, event):
        await self.send(text_data=json.dumps({
            'action': 'chat_deleted',
            'sender': event['sender'],
            'receiver': event['receiver']
        }))