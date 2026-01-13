"""
Webhooks Module - Recebe eventos externos.
"""
from app.modules.webhooks.handlers.zapi import ZAPIWebhookHandler
from app.modules.webhooks.handlers.n8n import N8NWebhookHandler

__all__ = [
    "ZAPIWebhookHandler",
    "N8NWebhookHandler",
]