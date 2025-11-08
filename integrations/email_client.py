# -*- coding: utf-8 -*-
"""
Email Client (Phase 5)
Minimal IMAP/SMTP using env configuration.

Env:
- EMAIL_HOST_IMAP, EMAIL_PORT_IMAP (default 993)
- EMAIL_HOST_SMTP, EMAIL_PORT_SMTP (default 587)
- EMAIL_USERNAME, EMAIL_PASSWORD
- EMAIL_USE_TLS (default true)
"""
import logging
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from typing import List, Tuple, Dict, Optional


def _env_bool(name: str, default: bool = True) -> bool:
	val = os.environ.get(name)
	if val is None:
		return default
	return str(val).lower() in ("1", "true", "yes", "on")


class EmailClient:
    def __init__(self, smtp_host: Optional[str] = None, smtp_port: Optional[int] = None,
                 username: Optional[str] = None, password: Optional[str] = None, use_tls: bool = True):
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST")
        self.smtp_port = int(smtp_port or os.environ.get("SMTP_PORT") or 587)
        self.username = username or os.environ.get("SMTP_USER")
        self.password = password or os.environ.get("SMTP_PASS")
        self.use_tls = use_tls

    def available(self) -> bool:
        return all([self.smtp_host, self.smtp_port, self.username, self.password])

    def send_mail(self, to_addr: str, subject: str, body: str, from_addr: Optional[str] = None) -> bool:
        if not self.available():
            logging.warning("EmailClient not configured")
            return False
        msg = MIMEText(body, 'plain', 'utf-8')
        msg["Subject"] = subject
        msg["From"] = from_addr or self.username
        msg["To"] = to_addr
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as s:
                if self.use_tls:
                    s.starttls()
                s.login(self.username, self.password)
                s.send_message(msg)
            return True
        except Exception:
            logging.exception("EmailClient.send_mail failed")
            return False


def fetch_email_summaries(limit: int = 10) -> Tuple[bool, List[Dict]]:
	"""Fetch recent email summaries from INBOX."""
	imap_host = os.environ.get('EMAIL_HOST_IMAP')
	imap_port = int(os.environ.get('EMAIL_PORT_IMAP', '993'))
	username = os.environ.get('EMAIL_USERNAME')
	password = os.environ.get('EMAIL_PASSWORD')
	if not (imap_host and username and password):
		return False, [{"error": "Missing IMAP env configuration"}]
	items: List[Dict] = []
	try:
		M = imaplib.IMAP4_SSL(imap_host, imap_port)
		M.login(username, password)
		M.select('INBOX')
		status, data = M.search(None, 'ALL')
		if status != 'OK':
			M.logout()
			return False, [{"error": "Search failed"}]
		ids = data[0].split()
		for msg_id in reversed(ids[-limit:]):
			status, msg_data = M.fetch(msg_id, '(RFC822.HEADER)')
			if status != 'OK':
				continue
			msg = email.message_from_bytes(msg_data[0][1])
			subj = msg.get('Subject', '')
			from_ = msg.get('From', '')
			date_ = msg.get('Date', '')
			items.append({"from": from_, "subject": subj, "date": date_})
		M.logout()
		return True, items
	except Exception:
		return False, [{"error": "IMAP fetch failed"}]


def send_email(to_address: str, subject: str, body: str) -> Tuple[bool, str]:
	"""Send a simple text email via SMTP."""
	smtp_host = os.environ.get('EMAIL_HOST_SMTP')
	smtp_port = int(os.environ.get('EMAIL_PORT_SMTP', '587'))
	username = os.environ.get('EMAIL_USERNAME')
	password = os.environ.get('EMAIL_PASSWORD')
	use_tls = _env_bool('EMAIL_USE_TLS', True)
	if not (smtp_host and username and password):
		return False, 'Missing SMTP env configuration'
	try:
		msg = MIMEText(body, 'plain', 'utf-8')
		msg['Subject'] = subject
		msg['From'] = username
		msg['To'] = to_address
		server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
		if use_tls:
			server.starttls()
		server.login(username, password)
		server.sendmail(username, [to_address], msg.as_string())
		server.quit()
		return True, 'Email sent'
	except Exception:
		return False, 'SMTP send failed'


