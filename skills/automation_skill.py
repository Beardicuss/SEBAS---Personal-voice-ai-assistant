# -*- coding: utf-8 -*-
"""
Automation Skill
Phase 5.1: Workflow automation and script execution
"""

from sebas.skills.base_skill import BaseSkill
from typing import Dict, Any
import logging
import platform
from datetime import datetime, timedelta


class AutomationSkill(BaseSkill):
    """
    Skill for managing automation workflows and scripts.
    """

    def __init__(self, assistant):
        super().__init__(assistant)
        self.intents = [
            'create_workflow',
            'execute_workflow',
            'list_workflows',
            'delete_workflow',
            'execute_powershell',
            'execute_batch',
            'execute_python',
            'create_scheduled_task',
            'list_scheduled_tasks',
            'run_scheduled_task',
            'delete_scheduled_task',
            # Phase 5: Reminders
            'set_reminder',
            'list_reminders',
            'cancel_reminder',
            # Phase 5: Calendar
            'add_calendar_event',
            'list_calendar_events',
            'update_calendar_event',
            'delete_calendar_event'
        ]
        self.automation_engine = None
        self.script_executor = None
        self.task_scheduler = None
        self._init_managers()

    def _init_managers(self):
        """Initialize automation managers."""
        try:
            from sebas.integrations.automation_engine import AutomationEngine
            from sebas.integrations.script_executor import ScriptExecutor
            from sebas.integrations.task_scheduler import TaskScheduler
            self.automation_engine = AutomationEngine()
            self.script_executor = ScriptExecutor()
            self.task_scheduler = TaskScheduler() if platform.system() == 'Windows' else None
        except Exception:
            logging.exception("Failed to initialize automation managers")
            self.automation_engine = None
            self.script_executor = None
            self.task_scheduler = None

    # =============== Intent handling ===============

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def get_intents(self) -> list:
        return self.intents

    def handle(self, intent: str, slots: dict) -> bool:
        if intent == 'create_workflow':
            return self._handle_create_workflow(slots)
        elif intent == 'execute_workflow':
            return self._handle_execute_workflow(slots)
        elif intent == 'list_workflows':
            return self._handle_list_workflows()
        elif intent == 'delete_workflow':
            return self._handle_delete_workflow(slots)
        elif intent == 'execute_powershell':
            return self._handle_execute_powershell(slots)
        elif intent == 'execute_batch':
            return self._handle_execute_batch(slots)
        elif intent == 'execute_python':
            return self._handle_execute_python(slots)
        elif intent == 'create_scheduled_task':
            return self._handle_create_scheduled_task(slots)
        elif intent == 'list_scheduled_tasks':
            return self._handle_list_scheduled_tasks()
        elif intent == 'run_scheduled_task':
            return self._handle_run_scheduled_task(slots)
        elif intent == 'delete_scheduled_task':
            return self._handle_delete_scheduled_task(slots)
        elif intent == 'set_reminder':
            return self._handle_set_reminder(slots)
        elif intent == 'list_reminders':
            return self._handle_list_reminders()
        elif intent == 'cancel_reminder':
            return self._handle_cancel_reminder(slots)
        elif intent == 'read_emails':
            return self._handle_read_emails(slots)
        elif intent == 'send_email':
            return self._handle_send_email(slots)
        elif intent == 'add_calendar_event':
            return self._handle_add_calendar_event(slots)
        elif intent == 'list_calendar_events':
            return self._handle_list_calendar_events(slots)
        elif intent == 'update_calendar_event':
            return self._handle_update_calendar_event(slots)
        elif intent == 'delete_calendar_event':
            return self._handle_delete_calendar_event(slots)
        return False

    # ===================== Workflows =====================

    def _handle_create_workflow(self, slots: dict) -> bool:
        if not self.assistant.has_permission('create_workflow'):
            return False
        try:
            if not self.automation_engine:
                self.assistant.speak("Automation engine not available")
                return False

            workflow_name = slots.get('name')
            if not workflow_name:
                self.assistant.speak("Please specify a workflow name")
                return False

            self.automation_engine.create_workflow(workflow_name)
            self.assistant.speak(f"Workflow {workflow_name} created")
            return True

        except Exception:
            logging.exception("Failed to create workflow")
            self.assistant.speak("Failed to create workflow")
            return False

    def _handle_execute_workflow(self, slots: dict) -> bool:
        if not self.assistant.has_permission('execute_workflow'):
            return False

        try:
            if not self.automation_engine:
                self.assistant.speak("Automation engine not available")
                return False

            workflow_name = slots.get('name')
            if not workflow_name:
                self.assistant.speak("Please specify a workflow name")
                return False

            workflow = self.automation_engine.execute_workflow(workflow_name)
            if workflow:
                status = workflow.status.value
                self.assistant.speak(f"Workflow {workflow_name} executed with status: {status}")
            else:
                self.assistant.speak(f"Workflow {workflow_name} not found")

            return workflow is not None

        except Exception:
            logging.exception("Failed to execute workflow")
            self.assistant.speak("Failed to execute workflow")
            return False

    def _handle_list_workflows(self) -> bool:
        try:
            if not self.automation_engine:
                self.assistant.speak("Automation engine not available")
                return False

            workflows = self.automation_engine.list_workflows()

            if workflows:
                self.assistant.speak(f"Found {len(workflows)} workflows: {', '.join(workflows[:10])}")
            else:
                self.assistant.speak("No workflows found")

            return True

        except Exception:
            logging.exception("Failed to list workflows")
            self.assistant.speak("Failed to list workflows")
            return False

    def _handle_delete_workflow(self, slots: dict) -> bool:
        if not self.assistant.has_permission('delete_workflow'):
            return False

        try:
            if not self.automation_engine:
                self.assistant.speak("Automation engine not available")
                return False

            workflow_name = slots.get('name')
            if not workflow_name:
                self.assistant.speak("Please specify a workflow name")
                return False

            success = self.automation_engine.delete_workflow(workflow_name)
            if success:
                self.assistant.speak(f"Workflow {workflow_name} deleted")
            else:
                self.assistant.speak(f"Workflow {workflow_name} not found")

            return success

        except Exception:
            logging.exception("Failed to delete workflow")
            self.assistant.speak("Failed to delete workflow")
            return False

    # ===================== Script Execution =====================

    def _handle_execute_powershell(self, slots: dict) -> bool:
        if not self.assistant.has_permission('execute_powershell'):
            return False

        try:
            if not self.script_executor:
                self.assistant.speak("Script executor not available")
                return False

            script = slots.get('script')
            if not script:
                self.assistant.speak("Please specify a PowerShell script")
                return False

            success, stdout, stderr = self.script_executor.execute_powershell(script)

            if success:
                self.assistant.speak("PowerShell script executed successfully")
            else:
                self.assistant.speak(f"Script execution failed: {stderr[:100]}")

            return success

        except Exception:
            logging.exception("Failed to execute PowerShell")
            self.assistant.speak("Failed to execute PowerShell script")
            return False

    def _handle_execute_batch(self, slots: dict) -> bool:
        if not self.assistant.has_permission('execute_batch'):
            return False

        try:
            if not self.script_executor:
                self.assistant.speak("Script executor not available")
                return False

            script = slots.get('script')
            if not script:
                self.assistant.speak("Please specify a batch script")
                return False

            success, stdout, stderr = self.script_executor.execute_batch(script)

            if success:
                self.assistant.speak("Batch script executed successfully")
            else:
                self.assistant.speak(f"Script execution failed: {stderr[:100]}")

            return success

        except Exception:
            logging.exception("Failed to execute batch")
            self.assistant.speak("Failed to execute batch script")
            return False

    def _handle_execute_python(self, slots: dict) -> bool:
        if not self.assistant.has_permission('execute_python'):
            return False

        try:
            if not self.script_executor:
                self.assistant.speak("Script executor not available")
                return False

            script = slots.get('script')
            if not script:
                self.assistant.speak("Please specify a Python script")
                return False

            success, stdout, stderr = self.script_executor.execute_python(script)

            if success:
                self.assistant.speak("Python script executed successfully")
            else:
                self.assistant.speak(f"Script execution failed: {stderr[:100]}")

            return success

        except Exception:
            logging.exception("Failed to execute Python")
            self.assistant.speak("Failed to execute Python script")
            return False

    # ===================== Scheduled Tasks =====================

    def _handle_create_scheduled_task(self, slots: dict) -> bool:
        if not self.assistant.has_permission('create_scheduled_task'):
            return False

        try:
            if not self.task_scheduler:
                self.assistant.speak("Task scheduler not available")
                return False

            task_name = slots.get('name')
            command = slots.get('command')

            if not task_name or not command:
                self.assistant.speak("Please specify task name and command")
                return False

            from sebas.integrations.task_scheduler import TaskTriggerType
            trigger_type = TaskTriggerType.DAILY

            success, message = self.task_scheduler.create_task(
                task_name=task_name,
                command=command,
                trigger_type=trigger_type
            )

            self.assistant.speak(message)
            return success

        except Exception:
            logging.exception("Failed to create scheduled task")
            self.assistant.speak("Failed to create scheduled task")
            return False

    def _handle_list_scheduled_tasks(self) -> bool:
        try:
            if not self.task_scheduler:
                self.assistant.speak("Task scheduler not available")
                return False

            tasks = self.task_scheduler.list_tasks()

            if tasks:
                self.assistant.speak(f"Found {len(tasks)} scheduled tasks")
            else:
                self.assistant.speak("No scheduled tasks found")

            return True

        except Exception:
            logging.exception("Failed to list scheduled tasks")
            self.assistant.speak("Failed to list scheduled tasks")
            return False

    def _handle_run_scheduled_task(self, slots: dict) -> bool:
        if not self.assistant.has_permission('run_scheduled_task'):
            return False

        try:
            if not self.task_scheduler:
                self.assistant.speak("Task scheduler not available")
                return False

            task_name = slots.get('name')
            if not task_name:
                self.assistant.speak("Please specify a task name")
                return False

            success, message = self.task_scheduler.run_task(task_name)
            self.assistant.speak(message)
            return success

        except Exception:
            logging.exception("Failed to run scheduled task")
            self.assistant.speak("Failed to run scheduled task")
            return False

    def _handle_delete_scheduled_task(self, slots: dict) -> bool:
        if not self.assistant.has_permission('delete_scheduled_task'):
            return False

        try:
            if not self.task_scheduler:
                self.assistant.speak("Task scheduler not available")
                return False

            task_name = slots.get('name')
            if not task_name:
                self.assistant.speak("Please specify a task name")
                return False

            success, message = self.task_scheduler.delete_task(task_name)
            self.assistant.speak(message)
            return success

        except Exception:
            logging.exception("Failed to delete scheduled task")
            self.assistant.speak("Failed to delete scheduled task")
            return False

    # ===================== Reminders =====================

    def _reminders_store_path(self) -> str:
        import os
        return os.path.join(os.path.expanduser('~'), '.sebas_reminders.json')

    def _load_reminders(self):
        import os, json
        path = self._reminders_store_path()
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_reminders(self, items):
        import json
        with open(self._reminders_store_path(), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def _schedule_reminder(self, when_ts: float, message: str, reminder_id: str):
        import threading, time

        def _timer():
            delay = max(0.0, when_ts - time.time())
            if delay:
                time.sleep(delay)
            try:
                self.assistant.speak(f"Reminder: {message}")
            except Exception:
                logging.exception("reminder speak failed")

        t = threading.Thread(target=_timer, daemon=True)
        t.start()

    def _handle_set_reminder(self, slots: dict) -> bool:
        try:
            message = (slots.get('message') or 'Reminder').strip()
            when = slots.get('when')

            if not when:
                amount = int(slots.get('minutes', 0))
                seconds = int(slots.get('seconds', 0))
                if amount == 0 and seconds == 0:
                    self.assistant.speak("Please specify when to remind you")
                    return False
                import time
                when_ts = time.time() + (amount * 60 + seconds)
            else:
                import datetime as dt
                try:
                    if isinstance(when, (int, float)):
                        when_ts = float(when)
                    else:
                        dt_val = dt.datetime.fromisoformat(str(when))
                        when_ts = dt_val.timestamp()
                except Exception:
                    self.assistant.speak("I couldn't parse the time")
                    return False

            import uuid
            reminder_id = str(uuid.uuid4())[:8]
            items = self._load_reminders()
            items.append({"id": reminder_id, "when": when_ts, "message": message})
            self._save_reminders(items)
            self._schedule_reminder(when_ts, message, reminder_id)
            self.assistant.speak("Reminder set")
            return True

        except Exception:
            logging.exception("set_reminder failed")
            self.assistant.speak("Failed to set reminder")
            return False

    def _handle_list_reminders(self) -> bool:
        try:
            import time
            items = self._load_reminders()
            if not items:
                self.assistant.speak("No reminders scheduled")
                return True

            upcoming = [it for it in items if it.get('when', 0) > time.time()]
            if not upcoming:
                self.assistant.speak("No upcoming reminders")
                return True

            upcoming = sorted(upcoming, key=lambda x: x.get('when', 0))
            summary = []
            for it in upcoming[:5]:
                ts = it.get('when', 0)
                summary.append(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M'))
            self.assistant.speak(f"Upcoming reminders: {', '.join(summary)}")
            return True

        except Exception:
            logging.exception("list_reminders failed")
            self.assistant.speak("Failed to list reminders")
            return False

    def _handle_cancel_reminder(self, slots: dict) -> bool:
        try:
            rid = (slots.get('id') or '').strip()
            if not rid:
                self.assistant.speak("Please specify the reminder id")
                return False

            items = self._load_reminders()
            new_items = [it for it in items if it.get('id') != rid]
            if len(new_items) == len(items):
                self.assistant.speak("Reminder not found")
                return False

            self._save_reminders(new_items)
            self.assistant.speak("Reminder cancelled")
            return True

        except Exception:
            logging.exception("cancel_reminder failed")
            self.assistant.speak("Failed to cancel reminder")
            return False

    # ===================== Email =====================

    def _handle_read_emails(self, slots: dict) -> bool:
        try:
            limit = int(slots.get('limit', 5))
            from sebas.integrations.email_client import fetch_email_summaries
            ok, items = fetch_email_summaries(limit=limit)
            if not ok:
                self.assistant.speak("Failed to read emails")
                return False

            if not items:
                self.assistant.speak("No recent emails")
                return True

            top = items[:3]
            subjects = ", ".join((i.get('subject') or 'No subject') for i in top)
            self.assistant.speak(f"Recent emails: {subjects}")
            return True

        except Exception:
            logging.exception("read_emails failed")
            self.assistant.speak("Failed to read emails")
            return False

    def _handle_send_email(self, slots: dict) -> bool:
        try:
            to_addr = (slots.get('to') or '').strip()
            subject = (slots.get('subject') or '').strip()
            body = (slots.get('body') or '').strip()

            if not to_addr or not subject or not body:
                self.assistant.speak("Please specify recipient, subject, and message")
                return False

            from sebas.integrations.email_client import send_email
            ok, msg = send_email(to_addr, subject, body)
            self.assistant.speak(msg)
            return ok

        except Exception:
            logging.exception("send_email failed")
            self.assistant.speak("Failed to send email")
            return False

    # ===================== Calendar =====================

    def _handle_add_calendar_event(self, slots: dict) -> bool:
        try:
            provider = (slots.get('provider') or 'microsoft')
            title = (slots.get('title') or '').strip()
            start_iso = (slots.get('start_iso') or '').strip()
            end_iso = (slots.get('end_iso') or '').strip()
            description = (slots.get('description') or '').strip()
            natural = (slots.get('natural') or '').strip()

            if natural and (not start_iso or not end_iso):
                ok, parsed = self._parse_natural_event(natural)
                if not ok:
                    self.assistant.speak("I couldn't parse the event time. Please specify start and end.")
                    return False
                if not title:
                    title = parsed.get('title', title)
                start_iso = parsed.get('start_iso', start_iso)
                end_iso = parsed.get('end_iso', end_iso)

            if not title or not start_iso or not end_iso:
                self.assistant.speak("Please specify title, start, and end time")
                return False

            from sebas.integrations.calendar_client import CalendarClient
            client = CalendarClient()
            ok, msg = client.add_event(provider, title, start_iso, end_iso, description)
            self.assistant.speak(msg)
            return ok

        except Exception:
            logging.exception("add_calendar_event failed")
            self.assistant.speak("Failed to add calendar event")
            return False

    # ===================== Natural language event parsing =====================

    def _parse_natural_event(self, text: str):
        """
        Parse natural language event time.
        Returns (ok, {start_iso, end_iso, title})
        """
        try:
            import re
            now = datetime.now()

            txt = text.lower().strip()

            # Duration
            dur_minutes = None
            m = re.search(r"for\s+(\d{1,3})\s*(minutes?|mins?|m)\b", txt)
            if m:
                dur_minutes = int(m.group(1))
            else:
                m = re.search(r"for\s+(\d{1,2})\s*(hours?|hrs?|h)\b", txt)
                if m:
                    dur_minutes = int(m.group(1)) * 60

            if dur_minutes is None:
                dur_minutes = 30

            txt_clean = re.sub(
                r"for\s+\d{1,3}\s*(minutes?|mins?|m|hours?|hrs?|h)\b",
                "",
                txt
            ).strip()

            # Date parsing
            date_dt = None

            # YYYY-MM-DD
            m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", txt_clean)
            if m:
                y, mo, d = map(int, m.groups())
                date_dt = datetime(y, mo, d)
                txt_clean = txt_clean.replace(m.group(0), '').strip()

            # Time
            time_hour = None
            time_minute = 0
            ampm = None

            # hh:mm
            m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", txt_clean)
            if m:
                time_hour = int(m.group(1))
                time_minute = int(m.group(2))
                ampm = m.group(3)
                txt_clean = txt_clean.replace(m.group(0), '').strip()

            # hh am/pm
            if time_hour is None:
                m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", txt_clean)
                if m:
                    time_hour = int(m.group(1))
                    ampm = m.group(2)
                    txt_clean = txt_clean.replace(m.group(0), '').strip()

            if time_hour is None:
                return False, {}

            if ampm == 'pm' and time_hour < 12:
                time_hour += 12
            if ampm == 'am' and time_hour == 12:
                time_hour = 0

            base_day = date_dt or now
            start_dt = base_day.replace(
                hour=time_hour,
                minute=time_minute,
                second=0,
                microsecond=0
            )
            end_dt = start_dt + timedelta(minutes=dur_minutes)

            return True, {
                "start_iso": start_dt.isoformat(),
                "end_iso": end_dt.isoformat(),
                "title": text
            }

        except Exception:
            logging.exception("parse_natural_event failed")
            return False, {}

    def _handle_list_calendar_events(self, slots: dict) -> bool:
        try:
            provider = (slots.get('provider') or 'microsoft')
            from sebas.integrations.calendar_client import CalendarClient
            client = CalendarClient()

            ok, events = client.list_events(provider)
            if not ok:
                self.assistant.speak("Failed to list events")
                return False

            if not events:
                self.assistant.speak("No events found")
                return True

            titles = ", ".join(e.get('subject', 'No title') for e in events[:5])
            self.assistant.speak(f"Upcoming events: {titles}")
            return True

        except Exception:
            logging.exception("list_calendar_events failed")
            self.assistant.speak("Failed to list events")
            return False

    def _handle_update_calendar_event(self, slots: dict) -> bool:
        try:
            provider = slots.get('provider', 'microsoft')
            event_id = slots.get('id')
            title = slots.get('title')
            start_iso = slots.get('start_iso')
            end_iso = slots.get('end_iso')
            desc = slots.get('description')

            if not event_id:
                self.assistant.speak("Please specify event id")
                return False

            from sebas.integrations.calendar_client import CalendarClient
            client = CalendarClient()

            ok, msg = client.update_event(provider, event_id, title, start_iso, end_iso, desc)
            self.assistant.speak(msg)
            return ok

        except Exception:
            logging.exception("update_calendar_event failed")
            self.assistant.speak("Failed to update event")
            return False

    def _handle_delete_calendar_event(self, slots: dict) -> bool:
        try:
            provider = slots.get('provider', 'microsoft')
            event_id = slots.get('id')

            if not event_id:
                self.assistant.speak("Please specify event id")
                return False

            from sebas.integrations.calendar_client import CalendarClient
            client = CalendarClient()

            ok, msg = client.delete_event(provider, event_id)
            self.assistant.speak(msg)
            return ok

        except Exception:
            logging.exception("delete_calendar_event failed")
            self.assistant.speak("Failed to delete event")
            return False
