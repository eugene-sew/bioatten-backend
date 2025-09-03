from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/attendance/updates/(?P<schedule_id>\w+)/$', consumers.AttendanceUpdateConsumer.as_asgi()),
]
