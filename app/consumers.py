import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatMessage, OTP, Product
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sender = self.scope["user"]
        self.receiver = self.scope["url_route"]["kwargs"]["receiver"]
        self.room_name = f"chat_{self.sender}_{self.receiver}"
        self.room_group_name = f"chat_{self.sender}_{self.receiver}"

        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        sender = data["sender"]
        receiver = data["receiver"]
        message = data["message"]
        product_id = data.get("product_id")

        product = await sync_to_async(Product.objects.get)(id=product_id) if product_id else None
        sender_user = await sync_to_async(OTP.objects.get)(phone=sender)
        receiver_user = await sync_to_async(OTP.objects.get)(phone=receiver)

        chat_message = await sync_to_async(ChatMessage.objects.create)(
            sender=sender_user, receiver=receiver_user, message=message, product=product
        )

        await self.channel_layer.group_send(
            self.room_group_name, {
                "type": "chat_message",
                "message": message,
                "sender": sender,
                "receiver": receiver,
                "timestamp": str(chat_message.timestamp)
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
