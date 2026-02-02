"""Entity infrastructure for the living model.

This module provides:
- Entity Registry: who exists, how to reach them
- Channels: communication pathways
- Delivery: guaranteed message delivery with acknowledgment
- Subscriptions: who wants to know about what

Core principle: Every entity must be reachable. No silent failures.
"""

from .registry import EntityRegistry, Entity, EntityType, EntityStatus
from .channels import Channel, ModelChannel, ExternalChannel
from .delivery import MessageBus, Message, DeliveryResult
from .subscriptions import SubscriptionManager, Subscription
