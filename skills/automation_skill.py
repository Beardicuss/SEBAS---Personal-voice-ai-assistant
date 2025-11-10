# -*- coding: utf-8 -*-
"""
Automation Skill
Phase 5.1: Workflow automation and script execution
"""

from skills.base_skill import BaseSkill
from typing import Dict, Any
import logging
import platform
from datetime import datetime, timedelta
from integrations.email_client import EmailClient, fetch_email_summaries
client = EmailClient()
print(client.send_mail("me@domain.com", "Test", "Hello"))
print(fetch_email_summaries(2))
from integrations.ms_graph_auth import get_access_token
print(get_access_token())
from integrations.enterprise_integrations import JiraIntegration, DocumentationGenerator

jira = JiraIntegration("https://fake.atlassian.net", "user", "token")
ok, resp = jira.create_ticket("Test", "This is a test")
print(ok, resp)

docs = DocumentationGenerator().generate_configuration_documentation({"debug": True, "version": "1.0"})
print(docs[:200])
from integrations.event_system import EventSystem, EventType

sys = EventSystem()

def printer(event): 
    print(f"[EVENT] {event.event_type.value} from {event.source}")

sys.subscribe(EventType.CUSTOM, printer)
sys.publish_event(EventType.CUSTOM, "TestModule", {"hello": "world"})

from integrations.firewall_manager import FirewallManager, FirewallRuleDirection, FirewallRuleAction, FirewallRuleProtocol

fw = FirewallManager()
ok, msg = fw.create_firewall_rule("TestRule", FirewallRuleDirection.INBOUND, FirewallRuleAction.ALLOW, FirewallRuleProtocol.TCP, local_port=8080)
print(ok, msg)
ok, rules = fw.list_firewall_rules("TestRule")
print(rules)
fw.delete_firewall_rule("TestRule")

from integrations.file_operations import FileOperations
f = FileOperations()
ok, stats = f.copy_recursive("C:/temp/source", "C:/temp/dest", pattern="*.txt", overwrite=True)
print(ok, stats)
dupes = f.find_duplicate_files("C:/temp")
print("Duplicates:", dupes)




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
            from integrations.automation_engine import AutomationEngine
            from integrations.script_executor import ScriptExecutor
            from integrations.task_scheduler import TaskScheduler
            self.automation_engine = AutomationEngine()
            self.script_executor = ScriptExecutor()
            self.task_scheduler = TaskScheduler() if platform.system() == 'Windows' else None
        except Exception:
            logging.exception("Failed to initialize automation managers")
            self.automation_engine = None
            self.script_executor = None
            self.task_scheduler = None

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

    def _handle_create_workflow(self, slots: dict) -> bool:
        """Handle create workflow command."""
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
        """Handle execute workflow command."""
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
        """Handle list workflows command."""
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
        """Handle delete workflow command."""
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

    def _handle_execute_powershell(self, slots: dict) -> bool:
        """Handle execute PowerShell command."""
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
        """Handle execute batch command."""
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
        """Handle execute Python command."""
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

    def _handle_create_scheduled_task(self, slots: dict) -> bool:
        """Handle create scheduled task command."""
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

            from integrations.task_scheduler import TaskTriggerType
            trigger_type = TaskTriggerType.DAILY  # Default

            success, message = self.task_scheduler.create_task(
                task_name=task_name,
                command=command,
                trigger_type=trigger_type
            )

            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to create task: {message}")

            return success

        except Exception:
            logging.exception("Failed to create scheduled task")
            self.assistant.speak("Failed to create scheduled task")
            return False

    def _handle_list_scheduled_tasks(self) -> bool:
        """Handle list scheduled tasks command."""
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
        """Handle run scheduled task command."""
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

            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to run task: {message}")

            return success

        except Exception:
            logging.exception("Failed to run scheduled task")
            self.assistant.speak("Failed to run scheduled task")
            return False

    def _handle_delete_scheduled_task(self, slots: dict) -> bool:
        """Handle delete scheduled task command."""
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

            if success:
                self.assistant.speak(message)
            else:
                self.assistant.speak(f"Failed to delete task: {message}")

            return success

        except Exception:
            logging.exception("Failed to delete scheduled task")
            self.assistant.speak("Failed to delete scheduled task")
            return False

    # ----------------------- Phase 5: Reminders -----------------------
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
            # slots: when ('in 30 minutes' or absolute timestamp), message
            message = (slots.get('message') or 'Reminder').strip()
            when = slots.get('when')  # could be seconds offset or ISO string
            if not when:
                amount = int(slots.get('minutes', 0))
                seconds = int(slots.get('seconds', 0))
                if amount == 0 and seconds == 0:
                    self.assistant.speak("Please specify when to remind you")
                    return False
                delay = amount * 60 + seconds
                import time
                when_ts = time.time() + delay
            else:
                # parse when
                import time, datetime as dt_mod
                try:
                    if isinstance(when, (int, float)):
                        when_ts = float(when)
                    else:
                        # try ISO
                        dt = dt_mod.datetime.fromisoformat(str(when))
                        when_ts = dt.timestamp()
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
            items = sorted(items, key=lambda x: x.get('when', 0))
            upcoming = [it for it in items if it.get('when', 0) > time.time()]
            if not upcoming:
                self.assistant.speak("No upcoming reminders")
                return True

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

    # ----------------------- Phase 5: Email (IMAP/SMTP) -----------------------
    def _handle_read_emails(self, slots: dict) -> bool:
        try:
            limit = int(slots.get('limit', 5))
            from integrations.email_client import fetch_email_summaries
            ok, items = fetch_email_summaries(limit=limit)
            if not ok:
                self.assistant.speak(items[0].get('error', 'Failed to read emails'))
                return False
            if not items:
                self.assistant.speak("No recent emails")
                return True
            top = items[:min(3, len(items))]
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
            from integrations.email_client import send_email
            ok, msg = send_email(to_addr, subject, body)
            self.assistant.speak(msg)
            return ok
        except Exception:
            logging.exception("send_email failed")
            self.assistant.speak("Failed to send email")
            return False

    # ----------------------- Phase 5: Calendar (Microsoft Graph) -----------------------
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
                # Fill from parsed
                if not title:
                    title = parsed.get('title', '')
                start_iso = parsed.get('start_iso', start_iso)
                end_iso = parsed.get('end_iso', end_iso)

            if not title or not start_iso or not end_iso:
                self.assistant.speak("Please specify title, start, and end time")
                return False
            from integrations.calendar_client import CalendarClient
            client = CalendarClient()
            ok, msg = client.add_event(provider, title, start_iso, end_iso, description)
            self.assistant.speak(msg)
            return ok
        except Exception:
            logging.exception("add_calendar_event failed")
            self.assistant.speak("Failed to add calendar event")
            return False

    # ----------------------- Natural language parsing for events -----------------------
    def _parse_natural_event(self, text: str):
        """
        Parse phrases like: "tomorrow at 3 pm for 30 minutes", "today at 14:00 for 1 hour",
        "on Monday at 9 am for 45 minutes". Returns (ok, {start_iso, end_iso, title}).
        """
        try:
            import re
            now = datetime.now()

            txt = text.lower().strip()

            # Extract duration: "for X minutes|minute|hours|hour|h|m"
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

            # Remove the duration phrase for cleaner time parsing
            txt_clean = re.sub(r"for\s+\d{1,3}\s*(minutes?|mins?|m|hours?|hrs?|h)\b", "", txt).strip()

            # Determine base day: specific date, next week, today/tomorrow or weekday
            start_day = now

            # 1) Specific dates: ISO YYYY-MM-DD, M/D[/YYYY], or Month Name D[, YYYY]
            date_dt = None
            # ISO date
            m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", txt_clean)
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                date_dt = datetime(y, mo, d)
                txt_clean = txt_clean.replace(m.group(0), '').strip()
            else:
                # M/D or M/D/YYYY
                m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", txt_clean)
                if m:
                    mo, d = int(m.group(1)), int(m.group(2))
                    y = int(m.group(3)) if m.group(3) else now.year
                    if y < 100:
                        y += 2000
                    date_dt = datetime(y, mo, d)
                    txt_clean = txt_clean.replace(m.group(0), '').strip()
                else:
                    # Month name forms (Nov 12, 2025)
                    months = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
                        'oct': 10, 'nov': 11, 'dec': 12
                    }
                    m = re.search(
                        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
                        r"sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:,\s*(\d{4}))?\b",
                        txt_clean
                    )
                    if m:
                        mo = months[m.group(1)]
                        d = int(m.group(2))
                        y = int(m.group(3)) if m.group(3) else now.year
                        date_dt = datetime(y, mo, d)
                        txt_clean = txt_clean.replace(m.group(0), '').strip()

            if date_dt is not None:
                start_day = date_dt

            # 2) "next week" handling (optionally with weekday)
            if 'next week' in txt_clean:
                # Move to next week's Monday
                days_to_monday = (7 - now.weekday()) % 7
                if days_to_monday == 0:
                    days_to_monday = 7
                base_next_monday = now + timedelta(days=days_to_monday)
                # If a weekday specified, jump to that weekday after next Monday
                weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                found_wd = None
                for i, wd in enumerate(weekdays):
                    if wd in txt_clean:
                        found_wd = i
                        break
                if found_wd is None:
                    start_day = base_next_monday
                else:
                    start_day = base_next_monday + timedelta(days=found_wd)
                txt_clean = txt_clean.replace('next week', '').strip()

            if 'tomorrow' in txt_clean:
                start_day = now + timedelta(days=1)
                txt_clean = txt_clean.replace('tomorrow', '').strip()
            elif 'today' in txt_clean:
                txt_clean = txt_clean.replace('today', '').strip()
            else:
                # Weekday names
                weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                for i, wd in enumerate(weekdays):
                    if f'on {wd}' in txt_clean or wd in txt_clean:
                        # compute next weekday (including today if later time)
                        days_ahead = (i - now.weekday()) % 7
                        if days_ahead == 0:
                            days_ahead = 7
                        start_day = now + timedelta(days=days_ahead)
                        txt_clean = txt_clean.replace(f'on {wd}', '').replace(wd, '').strip()
                        break

            # Extract time: formats like 3 pm, 3:30 pm, 15:00
            hour = None
            minute = 0
            ampm = None
            m = re.search(r"at\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", txt_clean)
            if not m:
                # try bare time without 'at'
                m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", txt_clean)
            if m:
                hour = int(m.group(1))
                if m.group(2):
                    minute = int(m.group(2))
                if m.group(3):
                    ampm = m.group(3)
            else:
                # default to next whole hour
                hour = min(23, (now.hour + 1))
                minute = 0

            # Convert hour with am/pm
            if ampm == 'pm' and hour is not None and hour < 12:
                hour += 12
            if ampm == 'am' and hour == 12:
                hour = 0

            start_dt = start_day.replace(hour=hour or 9, minute=minute, second=0, microsecond=0)
            # If chosen time today but already past, move to next day at same time
            if start_dt < now:
                start_dt = start_dt + timedelta(days=1)

            end_dt = start_dt + timedelta(minutes=dur_minutes)
            start_iso = start_dt.strftime('%Y-%m-%dT%H:%M:%S')
            end_iso = end_dt.strftime('%Y-%m-%dT%H:%M:%S')

            # Title heuristic: remove time phrases and filler words
            title = re.sub(r"\b(at|on|today|tomorrow|for)\b", " ", text, flags=re.IGNORECASE)
            title = re.sub(r"\s+", " ", title).strip()
            if not title:
                title = 'Event'

            return True, {"start_iso": start_iso, "end_iso": end_iso, "title": title}
        except Exception:
            logging.exception("_parse_natural_event failed")
            return False, {}

    def _handle_list_calendar_events(self, slots: dict) -> bool:
        try:
            provider = (slots.get('provider') or 'microsoft')
            start_iso = (slots.get('start_iso') or '').strip()
            end_iso = (slots.get('end_iso') or '').strip()
            top = int(slots.get('top', 5))
            if not start_iso or not end_iso:
                self.assistant.speak("Please specify start and end time window")
                return False
            from integrations.calendar_client import list_events
            ok, items = list_events(provider, start_iso, end_iso, top)
            if not ok:
                err = items[0].get('error', 'Failed to list events') if items else 'Failed to list events'
                self.assistant.speak(err)
                return False
            if not items:
                self.assistant.speak("No events found in that window")
                return True

            # Summarize titles and times for first few
            def _fmt(it):
                s = it.get('start', {}).get('dateTime') or ''
                t = it.get('subject') or 'Untitled'
                return f"{t} at {s}"

            summary = ", ".join(_fmt(it) for it in items[:min(5, len(items))])
            self.assistant.speak(f"Events: {summary}")
            return True
        except Exception:
            logging.exception("list_calendar_events failed")
            self.assistant.speak("Failed to list calendar events")
            return False

    def _handle_update_calendar_event(self, slots: dict) -> bool:
        try:
            provider = (slots.get('provider') or 'microsoft')
            event_id = (slots.get('event_id') or '').strip()
            if not event_id:
                self.assistant.speak("Please provide the event id")
                return False
            title = slots.get('title')
            start_iso = slots.get('start_iso')
            end_iso = slots.get('end_iso')
            description = slots.get('description')
            from integrations.calendar_client import update_event
            ok, msg = update_event(provider, event_id, title, start_iso, end_iso, description)
            self.assistant.speak(msg)
            return ok
        except Exception:
            logging.exception("update_calendar_event failed")
            self.assistant.speak("Failed to update calendar event")
            return False

    def _handle_delete_calendar_event(self, slots: dict) -> bool:
        try:
            provider = (slots.get('provider') or 'microsoft')
            event_id = (slots.get('event_id') or '').strip()
            if not event_id:
                self.assistant.speak("Please provide the event id")
                return False
            if not self.assistant.confirm_action(f"Delete event {event_id}?"):
                return True
            from integrations.calendar_client import delete_event
            ok, msg = delete_event(provider, event_id)
            self.assistant.speak(msg)
            return ok
        except Exception:
            logging.exception("delete_calendar_event failed")
            self.assistant.speak("Failed to delete calendar event")
            return False
