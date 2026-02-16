"""Test registry and implementations for django_stratagem tests."""

from __future__ import annotations

from django_stratagem.interfaces import ConditionalInterface, HierarchicalInterface, Interface
from django_stratagem.registry import HierarchicalRegistry, Registry


class TestStrategyRegistry(Registry):
    """Test registry for django_stratagem tests."""

    implementations_module = "test_implementations"
    label_attribute = "display_name"


class TestStrategy(Interface):
    """Base interface for test strategies."""

    registry = TestStrategyRegistry
    display_name = "Base Test Strategy"

    def execute(self) -> str:
        """Execute the strategy and return a result string."""
        raise NotImplementedError


class EmailStrategy(TestStrategy):
    """Email notification strategy."""

    slug = "email"
    display_name = "Email Strategy"
    description = "Send notifications via email"
    icon = "fa-solid fa-envelope"
    priority = 10

    def execute(self) -> str:
        return "email_sent"


class SMSStrategy(TestStrategy):
    """SMS notification strategy."""

    slug = "sms"
    display_name = "SMS Strategy"
    description = "Send notifications via SMS"
    icon = "fa-solid fa-message"
    priority = 20

    def execute(self) -> str:
        return "sms_sent"


class PushStrategy(TestStrategy):
    """Push notification strategy."""

    slug = "push"
    display_name = "Push Strategy"
    description = "Send push notifications"
    icon = "fa-solid fa-bell"
    priority = 30

    def execute(self) -> str:
        return "push_sent"


class ConditionalTestRegistry(Registry):
    """Test registry for conditional implementations."""

    implementations_module = "conditional_test_implementations"


class ConditionalTestInterface(ConditionalInterface):
    """Base interface for conditional test implementations."""

    registry = ConditionalTestRegistry


class PremiumFeature(ConditionalTestInterface):
    """Implementation only available to premium users."""

    slug = "premium_feature"
    display_name = "Premium Feature"

    @classmethod
    def is_available(cls, context: dict | None) -> bool:
        """Check if the feature is available based on user subscription."""
        if not context:
            return False
        user = context.get("user")
        if not user:
            return False
        return getattr(user, "is_premium", False)


class BasicFeature(ConditionalTestInterface):
    """Implementation available to all users."""

    slug = "basic_feature"
    display_name = "Basic Feature"


class ParentTestRegistry(Registry):
    """Parent registry for hierarchical testing."""

    implementations_module = "parent_test_implementations"


class ParentInterface(Interface):
    """Parent interface."""

    registry = ParentTestRegistry


class CategoryA(ParentInterface):
    """Category A parent."""

    slug = "category_a"
    display_name = "Category A"


class CategoryB(ParentInterface):
    """Category B parent."""

    slug = "category_b"
    display_name = "Category B"


class ChildTestRegistry(HierarchicalRegistry):
    """Child registry that depends on parent selection."""

    implementations_module = "child_test_implementations"
    parent_registry = ParentTestRegistry


class ChildInterface(HierarchicalInterface):
    """Child interface with parent relationships."""

    registry = ChildTestRegistry


class ChildOfA(ChildInterface):
    """Child implementation for Category A."""

    slug = "child_of_a"
    display_name = "Child of A"
    parent_slug = "category_a"


class ChildOfB(ChildInterface):
    """Child implementation for Category B."""

    slug = "child_of_b"
    display_name = "Child of B"
    parent_slug = "category_b"


class ChildOfBoth(ChildInterface):
    """Child implementation for both categories."""

    slug = "child_of_both"
    display_name = "Child of Both"
    parent_slugs = ["category_a", "category_b"]
