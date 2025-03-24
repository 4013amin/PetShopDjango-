import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
from .models import ChatMessage, OTP, Product
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sender = self.scope.get("user")

        if self.sender is None or self.sender.is_anonymous:
            await self.close(code=4001)  # Custom code for unauthorized
            return

        self.receiver = self.scope["url_route"]["kwargs"]["receiver"]
        self.room_name = f"chat_{self.sender.phone}_{self.receiver}"
        self.room_group_name = f"chat_{self.sender.phone}_{self.receiver}"

        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.channel_layer:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        try:
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
        except KeyError as e:
            await self.send(text_data=json.dumps({"error": f"Missing field: {str(e)}"}))
        except (OTP.DoesNotExist, Product.DoesNotExist) as e:
            await self.send(text_data=json.dumps({"error": f"Object not found: {str(e)}"}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": f"Server error: {str(e)}"}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
            "receiver": event["receiver"],
            "timestamp": event["timestamp"]
        }))