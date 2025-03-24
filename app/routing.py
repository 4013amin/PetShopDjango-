from django.urls import re_path
from app.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<sender>\w+)/(?P<receiver>\w+)/$', ChatConsumer.as_asgi()),
]