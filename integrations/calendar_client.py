# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
import os
import requests


class CalendarClient:
    """Calendar client scaffold for Microsoft Graph / Google Calendar.
    Keeps a last_event placeholder and exposes add_event(provider, ...).
    """

    def __init__(self):
        self._last_event = None

    def add_event_local(self, title: str, when: datetime, duration_minutes: int = 30) -> bool:
        try:
            self._last_event = {
                "title": title,
                "start": when,
                "end": when + timedelta(minutes=duration_minutes),
            }
            logging.info(f"Scheduled event: {title} at {when.isoformat()}")
            return True
        except Exception:
            logging.exception("CalendarClient.add_event_local failed")
            return False

    def add_event(self, provider: str, title: str, start_iso: str, end_iso: str, description: str = "") -> Tuple[bool, str]:
        provider = (provider or '').lower().strip()
        if provider in ("microsoft", "outlook", "graph"):
            token = os.environ.get('MS_GRAPH_TOKEN')
            if not token:
                # Try OAuth helper
                try:
                    from integrations.ms_graph_auth import get_access_token
                    ok, tok = get_access_token(scopes=['Calendars.ReadWrite','offline_access'])
                    if not ok or not tok:
                        return False, "Microsoft Graph not configured"
                    token = tok
                except Exception:
                    return False, "Microsoft Graph not configured"
            try:
                tz = os.environ.get('MS_GRAPH_TIMEZONE', 'UTC')
                calendar_id = os.environ.get('MS_GRAPH_CALENDAR_ID')
                base_url = 'https://graph.microsoft.com/v1.0/me'
                url = f"{base_url}/events" if not calendar_id else f"{base_url}/calendars/{calendar_id}/events"
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                body = {
                    "subject": title,
                    "body": {"contentType": "text", "content": description or ""},
                    "start": {"dateTime": start_iso, "timeZone": tz},
                    "end": {"dateTime": end_iso, "timeZone": tz}
                }
                resp = requests.post(url, headers=headers, json=body, timeout=15)
                if 200 <= resp.status_code < 300:
                    return True, "Event added to calendar"
                if resp.status_code == 401:
                    return False, "Unauthorized: MS_GRAPH_TOKEN invalid or expired"
                return False, f"Graph error {resp.status_code}: {resp.text[:120]}"
            except Exception as e:
                return False, "Failed to add event via Microsoft Graph"
        if provider in ("google", "gcal", "gcalendar"):
            if not os.environ.get('GOOGLE_CALENDAR_TOKEN'):
                return False, "Google Calendar not configured"
            return False, "Calendar add_event not implemented in scaffold"
        return False, "Unknown calendar provider"

    def last_event(self) -> Optional[dict]:
        return self._last_event


def _ensure_token(scopes: List[str]) -> Tuple[bool, Optional[str]]:
    token = os.environ.get('MS_GRAPH_TOKEN')
    if token:
        return True, token
    try:
        from integrations.ms_graph_auth import get_access_token
        ok, tok = get_access_token(scopes=scopes)
        if not ok or not tok:
            return False, None
        return True, tok
    except Exception:
        return False, None


def list_events(provider: str, start_iso: str, end_iso: str, top: int = 10) -> Tuple[bool, List[Dict]]:
    provider = (provider or '').lower().strip()
    if provider not in ("microsoft", "outlook", "graph"):
        return False, [{"error": "Unsupported provider"}]
    ok, token = _ensure_token(['Calendars.Read', 'offline_access'])
    if not ok or not token:
        return False, [{"error": "Microsoft Graph not configured"}]
    tz = os.environ.get('MS_GRAPH_TIMEZONE', 'UTC')
    calendar_id = os.environ.get('MS_GRAPH_CALENDAR_ID')
    base = 'https://graph.microsoft.com/v1.0/me'
    if calendar_id:
        url = f"{base}/calendars/{calendar_id}/calendarView"
    else:
        url = f"{base}/calendarView"
    params = {
        'startDateTime': start_iso,
        'endDateTime': end_iso,
        '$top': str(int(top)),
        '$orderby': 'start/dateTime'
    }
    headers = {
        'Authorization': f'Bearer {token}',
        'Prefer': f'outlook.timezone="{tz}"'
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if 200 <= r.status_code < 300:
            data = r.json()
            items = data.get('value', [])
            return True, items
        if r.status_code == 401:
            return False, [{"error": "Unauthorized: token invalid or expired"}]
        return False, [{"error": f"Graph error {r.status_code}"}]
    except Exception:
        return False, [{"error": "Failed to list events"}]


def update_event(provider: str, event_id: str, title: Optional[str] = None,
                 start_iso: Optional[str] = None, end_iso: Optional[str] = None,
                 description: Optional[str] = None) -> Tuple[bool, str]:
    provider = (provider or '').lower().strip()
    if provider not in ("microsoft", "outlook", "graph"):
        return False, "Unsupported provider"
    ok, token = _ensure_token(['Calendars.ReadWrite', 'offline_access'])
    if not ok or not token:
        return False, "Microsoft Graph not configured"
    if not event_id:
        return False, "Missing event id"
    tz = os.environ.get('MS_GRAPH_TIMEZONE', 'UTC')
    base = 'https://graph.microsoft.com/v1.0/me'
    url = f"{base}/events/{event_id}"
    body: Dict[str, Dict] = {}
    if title is not None:
        body['subject'] = title
    if description is not None:
        body['body'] = {"contentType": "text", "content": description}
    if start_iso is not None:
        body['start'] = {"dateTime": start_iso, "timeZone": tz}
    if end_iso is not None:
        body['end'] = {"dateTime": end_iso, "timeZone": tz}
    if not body:
        return False, "Nothing to update"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    try:
        r = requests.patch(url, headers=headers, json=body, timeout=15)
        if 200 <= r.status_code < 300:
            return True, "Event updated"
        if r.status_code == 401:
            return False, "Unauthorized: token invalid or expired"
        return False, f"Graph error {r.status_code}: {r.text[:120]}"
    except Exception:
        return False, "Failed to update event"


def delete_event(provider: str, event_id: str) -> Tuple[bool, str]:
    provider = (provider or '').lower().strip()
    if provider not in ("microsoft", "outlook", "graph"):
        return False, "Unsupported provider"
    ok, token = _ensure_token(['Calendars.ReadWrite', 'offline_access'])
    if not ok or not token:
        return False, "Microsoft Graph not configured"
    if not event_id:
        return False, "Missing event id"
    base = 'https://graph.microsoft.com/v1.0/me'
    url = f"{base}/events/{event_id}"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        r = requests.delete(url, headers=headers, timeout=15)
        if r.status_code in (204, 200):
            return True, "Event deleted"
        if r.status_code == 401:
            return False, "Unauthorized: token invalid or expired"
        return False, f"Graph error {r.status_code}: {r.text[:120]}"
    except Exception:
        return False, "Failed to delete event"

