# # -*- coding: utf-8 -*-
# """
# Email Client (Phase 5)
# Minimal IMAP/SMTP using environment configuration.

# Env:
# set EMAIL_HOST_SMTP=smtp.test.com
# set EMAIL_USERNAME=test@test.com
# set EMAIL_PASSWORD=123
# set EMAIL_USE_TLS=True
# """

# import os
# import imaplib
# import smtplib
# import email
# import logging
# from email.mime.text import MIMEText
# from typing import List, Tuple, Dict, Optional


# def _env_bool(name: str, default: bool = True) -> bool:
#     """Helper to parse boolean-like environment variables."""
#     val = os.environ.get(name)
#     if val is None:
#         return default
#     return str(val).lower() in ("1", "true", "yes", "on")


# class EmailClient:
#     """Simple SMTP email sender."""

#     def __init__(
#         self,
#         smtp_host: Optional[str] = None,
#         smtp_port: Optional[int] = None,
#         username: Optional[str] = None,
#         password: Optional[str] = None,
#         use_tls: Optional[bool] = True,
#     ):
#         self.smtp_host: str = smtp_host or os.environ.get("EMAIL_HOST_SMTP", "")
#         self.smtp_port: int = int(smtp_port or os.environ.get("EMAIL_PORT_SMTP") or 587)
#         self.username: str = username or os.environ.get("EMAIL_USERNAME", "")
#         self.password: str = password or os.environ.get("EMAIL_PASSWORD", "")
#         self.use_tls: bool = use_tls if use_tls is not None else _env_bool("EMAIL_USE_TLS", True)

#     def available(self) -> bool:
#         return all([self.smtp_host, self.smtp_port, self.username, self.password])

#     # def send_mail(self, to_addr: str, subject: str, body: str, from_addr: Optional[str] = None) -> bool:
#         """Send an email using configured SMTP settings."""
#         if not self.available():
#             logging.warning("[EmailClient] SMTP configuration missing.")
#             return False

#         msg = MIMEText(body, "plain", "utf-8")
#         msg["Subject"] = subject
#         msg["From"] = from_addr or self.username
#         msg["To"] = to_addr

#         host: str = self.smtp_host or ""
#         port: int = int(self.smtp_port or 25)
#         username: str = self.username or ""
#         password: str = self.password or ""

#         try:
#             with smtplib.SMTP(host, port, timeout=15) as server:
#                 if self.use_tls:
#                     server.starttls()
#                 server.login(username, password)
#                 server.send_message(msg)
#             logging.info(f"[EmailClient] Email sent to {to_addr}")
#             return True
#         except Exception:
#             logging.exception("[EmailClient] send_mail failed")
#             return False


# def fetch_email_summaries(limit: int = 10) -> Tuple[bool, List[Dict]]:
#     """Fetch recent email summaries from INBOX via IMAP."""
#     imap_host: str = os.environ.get("EMAIL_HOST_IMAP", "")
#     imap_port: int = int(os.environ.get("EMAIL_PORT_IMAP", "993"))
#     username: str = os.environ.get("EMAIL_USERNAME", "")
#     password: str = os.environ.get("EMAIL_PASSWORD", "")

#     if not (imap_host and username and password):
#         logging.warning("[EmailClient] Missing IMAP configuration.")
#         return False, [{"error": "Missing IMAP env configuration"}]

#     items: List[Dict] = []
#     M: Optional[imaplib.IMAP4_SSL] = None

#     try:
#         M = imaplib.IMAP4_SSL(imap_host, imap_port)
#         M.login(username, password)
#         M.select("INBOX")

#         status, data = M.search(None, "ALL")
#         if status != "OK" or not data or not data[0]:
#             return False, [{"error": "No messages found"}]

#         ids = data[0].split()
#         for msg_id in reversed(ids[-limit:]):
#             status, msg_data = M.fetch(msg_id, "(RFC822.HEADER)")
#             if status != "OK" or not msg_data or not msg_data[0]:
#                 continue

#             msg_bytes = msg_data[0][1]
#             if not isinstance(msg_bytes, (bytes, bytearray)):
#                 continue

#             msg = email.message_from_bytes(msg_bytes)
#             subj = msg.get("Subject", "(No Subject)")
#             from_ = msg.get("From", "(Unknown Sender)")
#             date_ = msg.get("Date", "")

#             items.append({"from": from_, "subject": subj, "date": date_})
#         return True, items

#     except Exception:
#         logging.exception("[EmailClient] IMAP fetch failed")
#         return False, [{"error": "IMAP fetch failed"}]
#     finally:
#         if M is not None:
#             try:
#                 M.logout()
#             except Exception:
#                 pass


# def send_email(to_address: str, subject: str, body: str) -> Tuple[bool, str]:
#     """Send a plain-text email using environment SMTP settings."""
#     smtp_host: str = os.environ.get("EMAIL_HOST_SMTP", "")
#     smtp_port: int = int(os.environ.get("EMAIL_PORT_SMTP", "587"))
#     username: str = os.environ.get("EMAIL_USERNAME", "")
#     password: str = os.environ.get("EMAIL_PASSWORD", "")
#     use_tls: bool = _env_bool("EMAIL_USE_TLS", True)

#     if not (smtp_host and username and password):
#         logging.warning("[EmailClient] Missing SMTP configuration.")
#         return False, "Missing SMTP env configuration"

#     try:
#         msg = MIMEText(body, "plain", "utf-8")
#         msg["Subject"] = subject
#         msg["From"] = username
#         msg["To"] = to_address

#         with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
#             if use_tls:
#                 server.starttls()
#             server.login(username, password)
#             server.send_message(msg)

#         logging.info(f"[EmailClient] Email sent to {to_address}")
#         return True, "Email sent"
#     except Exception:
#         logging.exception("[EmailClient] SMTP send failed")
#         return False, "SMTP send failed"
