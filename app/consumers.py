# app/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract sender and receiver from the URL route
        self.sender = self.scope['url_route']['kwargs']['sender']
        self.receiver = self.scope['url_route']['kwargs']['receiver']
        self.room_group_name = f"chat_{self.sender}_{self.receiver}"

        # Log after attributes are set
        logger.info(f"WebSocket connecting: {self.scope['path']}")
        logger.info(f"Sender: {self.sender}, Receiver: {self.receiver}")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected: {self.room_group_name}")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender = text_data_json['sender']
        receiver = text_data_json['receiver']

        # Send message to room group
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
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'receiver': event['receiver']
        }))