# -*- coding: utf-8 -*-
"""
Calendar Client Integration
Supports Microsoft Graph Calendar and scaffolding for Google Calendar.
"""

import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any


class CalendarClient:
    """Calendar client for Microsoft Graph and placeholder for Google Calendar."""

    def __init__(self):
        self._last_event: Optional[dict] = None

    def add_event_local(self, title: str, when: datetime, duration_minutes: int = 30) -> bool:
        try:
            self._last_event = {
                "title": title,
                "start": when,
                "end": when + timedelta(minutes=duration_minutes),
            }
            logging.info(f"Scheduled local event: {title} at {when.isoformat()}")
            return True
        except Exception:
            logging.exception("[CalendarClient] add_event_local failed")
            return False

    def add_event(self, provider: str, title: str, start_iso: str, end_iso: str, description: str = "") -> Tuple[bool, str]:
        provider = (provider or '').lower().strip()

        # ---------- Google Calendar ----------
        if provider in ("google", "gcal", "gcalendar"):
            logging.warning("[CalendarClient] Google Calendar add_event not implemented")
            raise NotImplementedError("Google Calendar API not implemented in scaffold")

        return False, "Unknown calendar provider"

    def last_event(self) -> Optional[dict]:
        """Return last locally scheduled event, if any."""
        return self._last_event
