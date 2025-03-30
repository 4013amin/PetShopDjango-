from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
import logging
from .models import ChatMessage, OTP

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # دریافت شماره‌های فرستنده و گیرنده از URL
        self.sender = self.scope['url_route']['kwargs']['sender']
        self.receiver = self.scope['url_route']['kwargs']['receiver']
        # مرتب‌سازی برای ایجاد نام گروه منحصربه‌فرد
        sorted_users = sorted([self.sender, self.receiver])
        self.room_group_name = f"chat_{sorted_users[0]}_{sorted_users[1]}"

        # لاگ اتصال
        logger.info(f"WebSocket connecting: {self.scope['path']}")
        # اضافه کردن کانال به گروه
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        # پذیرش اتصال WebSocket
        await self.accept()

        # دریافت پیام‌های قبلی به‌صورت غیرهمزمان
        messages = await sync_to_async(
            lambda: list(ChatMessage.objects.filter(
                sender__phone__in=[self.sender, self.receiver],
                receiver__phone__in=[self.sender, self.receiver]
            ).select_related('sender', 'receiver', 'reply_to', 'reply_to__sender'))
        )()

        # پردازش و ارسال پیام‌ها
        for msg in messages:
            # به‌روزرسانی وضعیت پیام به SEEN اگر گیرنده آن را ندیده باشد
            if self.receiver == msg.receiver.phone and msg.status != 'SEEN':
                msg.status = 'SEEN'
                await sync_to_async(msg.save)()

            # آماده‌سازی داده‌های پیام پاسخ‌داده‌شده (reply_to)
            reply_to_data = None
            if msg.reply_to:
                reply_to_data = {
                    'id': msg.reply_to.id,
                    'message': msg.reply_to.message,
                    'sender': msg.reply_to.sender.phone if msg.reply_to.sender else None,
                    'timestamp': msg.reply_to.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }

            # ساختار داده پیام برای ارسال
            message_data = {
                'id': msg.id,
                'message': msg.message,
                'sender': msg.sender.phone,
                'receiver': msg.receiver.phone,
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'status': msg.status,
                'reply_to': reply_to_data
            }
            # ارسال پیام به کلاینت
            await self.send(text_data=json.dumps(message_data))

            # ارسال پیام به گروه برای اطلاع‌رسانی به همه کاربران
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
        # حذف کانال از گروه هنگام قطع اتصال
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected: {self.room_group_name}")

    async def receive(self, text_data):
        # دریافت و پردازش داده‌های ارسالی از کلاینت
        text_data_json = json.loads(text_data)
        
        # بررسی اینکه آیا درخواست حذف چت است یا ارسال پیام جدید
        action = text_data_json.get('action')
        
        if action == 'delete_chat':
            sender_phone = text_data_json['sender']
            receiver_phone = text_data_json['receiver']
            
            # حذف تمام پیام‌های بین فرستنده و گیرنده
            await sync_to_async(ChatMessage.objects.filter(
                sender__phone=sender_phone,
                receiver__phone=receiver_phone
            ).delete)()
            await sync_to_async(ChatMessage.objects.filter(
                sender__phone=receiver_phone,
                receiver__phone=sender_phone
            ).delete)()

            # اطلاع‌رسانی به گروه درباره حذف چت
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_deleted',
                    'sender': sender_phone,
                    'receiver': receiver_phone
                }
            )
            return

        # اگر درخواست پیام جدید باشد
        message = text_data_json['message']
        sender_phone = text_data_json['sender']
        receiver_phone = text_data_json['receiver']
        status = text_data_json.get('status', 'SENT')
        reply_to_id = text_data_json.get('reply_to_id')

        # دریافت اطلاعات فرستنده و گیرنده
        sender_user = await sync_to_async(
            lambda: OTP.objects.filter(phone=sender_phone).first()
        )()
        receiver_user = await sync_to_async(
            lambda: OTP.objects.filter(phone=receiver_phone).first()
        )()

        # بررسی وجود فرستنده و گیرنده
        if not sender_user or not receiver_user:
            await self.send(text_data=json.dumps({'error': 'Sender or receiver does not exist.'}))
            return

        # دریافت پیام پاسخ‌داده‌شده (reply_to) در صورت وجود
        reply_to = None
        if reply_to_id:
            reply_to = await sync_to_async(
                lambda: ChatMessage.objects.filter(id=reply_to_id).select_related('sender').first()
            )()

        # ایجاد پیام جدید
        chat_message = await sync_to_async(
            lambda: ChatMessage.objects.create(
                sender=sender_user,
                receiver=receiver_user,
                message=message,
                status=status,
                reply_to=reply_to
            )
        )()

        # دریافت پیام ایجادشده با اطلاعات مرتبط
        chat_message = await sync_to_async(
            lambda: ChatMessage.objects.select_related('sender', 'receiver', 'reply_to', 'reply_to__sender').get(id=chat_message.id)
        )()

        # آماده‌سازی داده‌های reply_to
        reply_to_data = None
        if chat_message.reply_to:
            reply_to_data = {
                'id': chat_message.reply_to.id,
                'message': chat_message.reply_to.message,
                'sender': chat_message.reply_to.sender.phone if chat_message.reply_to.sender else None,
                'timestamp': chat_message.reply_to.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }

        # ارسال پیام به گروه
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

    # هندل کردن پیام‌های جدید
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

    # هندل کردن حذف چت
    async def chat_deleted(self, event):
        await self.send(text_data=json.dumps({
            'action': 'chat_deleted',
            'sender': event['sender'],
            'receiver': event['receiver']
        }))