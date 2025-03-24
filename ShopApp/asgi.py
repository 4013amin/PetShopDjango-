import os
import django  # Add this

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopApp.settings')
django.setup()  # Initialize Django here before importing anything

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from app import routing  # Import routing after setup

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
