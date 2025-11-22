# -*- coding: utf-8 -*-
"""
Webhook Management System
"""

import json
import logging
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Optional requests library
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests library not available. Webhook delivery will be disabled.")


class WebhookEvent(Enum):
    """Webhook event types"""
    COMMAND_EXECUTED = "command.executed"
    COMMAND_FAILED = "command.failed"
    SYSTEM_EVENT = "system.event"
    USER_ACTION = "user.action"
    ERROR_OCCURRED = "error.occurred"
    STATUS_CHANGED = "status.changed"


@dataclass
class Webhook:
    """Webhook configuration"""
    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None
    enabled: bool = True
    timeout: int = 5
    retry_count: int = 3
    retry_delay: int = 1


class WebhookManager:
    """
    Manages webhook subscriptions and delivery.
    """
    
    def __init__(self):
        self.webhooks: Dict[str, Webhook] = {}
        self.delivery_queue: List[Dict] = []
        self.queue_lock = threading.Lock()
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
    
    def register_webhook(self, webhook_id: str, webhook: Webhook) -> bool:
        """
        Register a new webhook.
        
        Args:
            webhook_id: Unique identifier for the webhook
            webhook: Webhook configuration
            
        Returns:
            True if registered successfully
        """
        self.webhooks[webhook_id] = webhook
        logging.info(f"Registered webhook {webhook_id} for events: {[e.value for e in webhook.events]}")
        
        if not self.running:
            self._start_worker()
        
        return True
    
    def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a webhook.
        
        Args:
            webhook_id: Webhook identifier
            
        Returns:
            True if unregistered successfully
        """
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            logging.info(f"Unregistered webhook {webhook_id}")
            return True
        return False
    
    def trigger_event(self, event: WebhookEvent, data: Dict[str, Any]):
        """
        Trigger a webhook event.
        
        Args:
            event: Event type
            data: Event data
        """
        # Find webhooks subscribed to this event
        matching_webhooks = [
            (webhook_id, webhook) for webhook_id, webhook in self.webhooks.items()
            if webhook.enabled and event in webhook.events
        ]
        
        if not matching_webhooks:
            return
        
        payload = {
            'event': event.value,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        # Queue delivery for each matching webhook
        for webhook_id, webhook in matching_webhooks:
            self._queue_delivery(webhook_id, webhook, payload)
    
    def _queue_delivery(self, webhook_id: str, webhook: Webhook, payload: Dict):
        """Queue a webhook delivery."""
        delivery = {
            'webhook_id': webhook_id,
            'webhook': webhook,
            'payload': payload,
            'attempts': 0,
            'next_retry': time.time()
        }
        
        with self.queue_lock:
            self.delivery_queue.append(delivery)
    
    def _start_worker(self):
        """Start the webhook delivery worker thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logging.info("Webhook delivery worker started")
    
    def _worker_loop(self):
        """Worker thread loop for delivering webhooks."""
        while self.running:
            try:
                # Process deliveries
                with self.queue_lock:
                    ready_deliveries = [
                        d for d in self.delivery_queue
                        if d['attempts'] == 0 or time.time() >= d['next_retry']
                    ]
                    self.delivery_queue = [
                        d for d in self.delivery_queue
                        if d not in ready_deliveries
                    ]
                
                for delivery in ready_deliveries:
                    self._deliver_webhook(delivery)
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception:
                logging.exception("Error in webhook worker loop")
    
    def _deliver_webhook(self, delivery: Dict):
        """Deliver a webhook."""
        if not REQUESTS_AVAILABLE:
            logging.warning("Webhook delivery skipped: requests library not available")
            return
        
        webhook_id = delivery['webhook_id']
        webhook = delivery['webhook']
        payload = delivery['payload']
        attempts = delivery['attempts']
        
        try:
            # Add signature if secret is configured
            headers = {'Content-Type': 'application/json'}
            if webhook.secret:
                import hmac
                import hashlib
                payload_str = json.dumps(payload, sort_keys=True)
                signature = hmac.new(
                    webhook.secret.encode(),
                    payload_str.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers['X-Sebas-Signature'] = f"sha256={signature}"
            
            # Send webhook
            response = requests.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=webhook.timeout
            )
            
            if response.status_code < 400:
                logging.debug(f"Webhook {webhook_id} delivered successfully")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
        except Exception as e:
            logging.warning(f"Webhook {webhook_id} delivery failed: {e}")
            attempts += 1
            
            # Retry if attempts remaining
            if attempts < webhook.retry_count:
                delivery['attempts'] = attempts
                delivery['next_retry'] = time.time() + (webhook.retry_delay * attempts)
                with self.queue_lock:
                    self.delivery_queue.append(delivery)
            else:
                logging.error(f"Webhook {webhook_id} failed after {attempts} attempts")
    
    def stop(self):
        """Stop the webhook manager."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)


# Global webhook manager instance
_webhook_manager: Optional[WebhookManager] = None


def init_webhook_manager():
    """Initialize the global webhook manager."""
    global _webhook_manager
    _webhook_manager = WebhookManager()


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager