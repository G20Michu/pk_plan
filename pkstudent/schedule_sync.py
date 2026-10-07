import json
import logging
import ssl
from datetime import date, time
from time import monotonic, sleep, time as current_time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
from django.db import connections, transaction
from django.utils import timezone

from pkstudent.models import ScheduleEvent


API_URL = "https://plany.wieik.pk.edu.pl/lib/tpl/kiwiki/wk_plan_api.php"
SYNC_INTERVAL_SECONDS = 10 * 60 + 30
logger = logging.getLogger(__name__)


def sync_schedule():
    url = f"{API_URL}?{urlencode({'action': 'load', 'db': 'stac', '_': int(current_time() * 1000)})}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "PkPlan schedule sync",
        },
    )
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=30, context=context) as response:
        payload = json.loads(response.read())

    if payload.get("ok") is not True or not isinstance(payload.get("data"), list):
        raise ValueError("API zwróciło nieprawidłową odpowiedź planu.")

    records = []
    for item in payload["data"]:
        records.append({
            "remote_id": str(item["id"]),
            "event_type": str(item.get("eventType") or ""),
            "group_label": str(item.get("group") or ""),
            "instructor": str(item.get("instructor") or ""),
            "room": str(item.get("room") or ""),
            "faculty": str(item.get("faculty") or ""),
            "start_date": date.fromisoformat(item["startDate"]),
            "end_date": date.fromisoformat(item["endDate"]),
            "start_time": time.fromisoformat(item["startTime"]),
            "duration_min": int(item.get("durationMin") or 0),
            "interval_weeks": max(1, int(item.get("intervalWeeks") or 1)),
            "excluded_dates": item.get("excludedDates") or [],
            "overrides": item.get("overrides") or {},
        })

    synced_at = timezone.now()
    remote_ids = [record["remote_id"] for record in records]
    with transaction.atomic():
        for record in records:
            remote_id = record.pop("remote_id")
            ScheduleEvent.objects.update_or_create(
                remote_id=remote_id,
                defaults={**record, "synced_at": synced_at},
            )
        if remote_ids:
            ScheduleEvent.objects.exclude(remote_id__in=remote_ids).delete()

    return len(records)


def run_schedule_sync_loop():
    next_sync = monotonic()
    while True:
        try:
            count = sync_schedule()
            logger.info("Schedule synchronization saved %s events.", count)
        except Exception:
            logger.exception("Schedule synchronization failed.")
        finally:
            connections.close_all()

        next_sync += SYNC_INTERVAL_SECONDS
        sleep(max(0, next_sync - monotonic()))