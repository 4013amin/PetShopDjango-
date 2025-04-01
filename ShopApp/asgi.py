import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# تنظیم DJANGO_SETTINGS_MODULE قبل از هر چیز
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopApp.settings')

# بارگذاری برنامه‌های Django
django_asgi_app = get_asgi_application()

# حالا می‌توانید ماژول‌های وابسته به مدل‌ها را ایمپورت کنید
import app.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            app.routing.websocket_urlpatterns
        )
    ),
})