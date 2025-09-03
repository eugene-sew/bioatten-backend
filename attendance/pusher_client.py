import os
import logging
from typing import Any, Dict

try:
    import pusher
except Exception:  # pragma: no cover
    pusher = None

logger = logging.getLogger(__name__)

PUSHER_APP_ID = os.getenv('PUSHER_APP_ID')
PUSHER_KEY = os.getenv('PUSHER_KEY')
PUSHER_SECRET = os.getenv('PUSHER_SECRET')
PUSHER_CLUSTER = os.getenv('PUSHER_CLUSTER', 'mt1')

_enabled = bool(PUSHER_APP_ID and PUSHER_KEY and PUSHER_SECRET)
_client = None

if _enabled and pusher is not None:
    try:
        _client = pusher.Pusher(
            app_id=PUSHER_APP_ID,
            key=PUSHER_KEY,
            secret=PUSHER_SECRET,
            cluster=PUSHER_CLUSTER,
            ssl=True,
        )
        logger.info("Pusher client initialized for cluster %s", PUSHER_CLUSTER)
    except Exception as e:  # pragma: no cover
        logger.error("Failed to initialize Pusher client: %s", e)
        _enabled = False


def pusher_enabled() -> bool:
    return _enabled and _client is not None


def trigger(channel: str, event: str, data: Dict[str, Any]) -> bool:
    """Trigger a Pusher event. Returns True if attempted without exception."""
    if not pusher_enabled():
        logger.debug("Pusher disabled or not configured. Skipping trigger: %s %s", channel, event)
        return False
    try:
        _client.trigger(channel, event, data)
        return True
    except Exception as e:  # pragma: no cover
        logger.error("Pusher trigger failed: %s", e)
        return False


def trigger_attendance_update(schedule_id: int, data: Dict[str, Any]) -> bool:
    """Trigger real-time attendance update for a specific schedule."""
    channel = f'schedule-{schedule_id}'
    return trigger(channel, 'attendance-update', data)


def trigger_faculty_notification(schedule_id: int, data: Dict[str, Any]) -> bool:
    """Trigger notification to faculty about attendance events."""
    channel = f'faculty-schedule-{schedule_id}'
    return trigger(channel, 'attendance-notification', data)
