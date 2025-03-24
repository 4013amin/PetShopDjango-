from django.urls import re_path
from app.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<receiver>[0-9]+)/$", ChatConsumer.as_asgi()),
]