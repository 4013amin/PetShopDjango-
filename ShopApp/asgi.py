import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import path
from app.consumers import ChatConsumer

# مقداردهی اولیه Django قبل از استفاده از مدل‌ها
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopApp.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/chat/<str:receiver>/", ChatConsumer.as_asgi()),
        ])
    ),
})
