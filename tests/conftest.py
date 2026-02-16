"""Pytest configuration for django_stratagem tests."""

import copy
import os

import pytest


def pytest_configure(config):
    """Configure pytest to use test settings."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")


@pytest.fixture(autouse=True)
def _clean_stratagem_registry():
    """Prevent test-local Registry subclasses from polluting the global registry."""
    from django_stratagem.registry import RegistryRelationship, django_stratagem_registry

    original_registry = list(django_stratagem_registry)
    original_relationships = copy.deepcopy(RegistryRelationship._relationships)
    original_implementations = {
        reg: dict(reg.implementations) for reg in django_stratagem_registry if hasattr(reg, "implementations")
    }
    yield
    django_stratagem_registry.clear()
    django_stratagem_registry.extend(original_registry)
    RegistryRelationship._relationships.clear()
    RegistryRelationship._relationships.update(original_relationships)
    for reg, impls in original_implementations.items():
        reg.implementations.clear()
        reg.implementations.update(impls)


@pytest.fixture(scope="function")
def register_test_implementations():
    """Register test implementations in the ExporterRegistry."""
    from tests.exporters.registry import ExporterRegistry

    ExporterRegistry.discover_implementations()

    yield ExporterRegistry

    ExporterRegistry.clear_cache()


@pytest.fixture(autouse=True)
def test_strategy_registry():
    """Register TestStrategyRegistry implementations for every test."""
    from tests.registries_fixtures import (
        EmailStrategy,
        PushStrategy,
        SMSStrategy,
        TestStrategyRegistry,
    )

    original_implementations = dict(TestStrategyRegistry.implementations)
    TestStrategyRegistry.register(EmailStrategy)
    TestStrategyRegistry.register(SMSStrategy)
    TestStrategyRegistry.register(PushStrategy)

    yield TestStrategyRegistry

    TestStrategyRegistry.implementations.clear()
    TestStrategyRegistry.implementations.update(original_implementations)
    TestStrategyRegistry.clear_cache()


@pytest.fixture
def test_registry(test_strategy_registry):
    """Alias for test_strategy_registry."""
    return test_strategy_registry


@pytest.fixture
def email_strategy():
    """Return EmailStrategy class."""
    from tests.registries_fixtures import EmailStrategy

    return EmailStrategy


@pytest.fixture
def sms_strategy():
    """Return SMSStrategy class."""
    from tests.registries_fixtures import SMSStrategy

    return SMSStrategy


@pytest.fixture
def push_strategy():
    """Return PushStrategy class."""
    from tests.registries_fixtures import PushStrategy

    return PushStrategy


@pytest.fixture
def registry_form_field(test_strategy_registry):
    """Return a RegistryFormField configured with test registry."""
    from django_stratagem.forms import RegistryFormField

    return RegistryFormField(
        registry=test_strategy_registry,
        choices=test_strategy_registry.get_choices(),
    )


@pytest.fixture
def parent_registry():
    """Return ParentTestRegistry with registered implementations."""
    from tests.registries_fixtures import (
        CategoryA,
        CategoryB,
        ParentTestRegistry,
    )

    original_implementations = dict(ParentTestRegistry.implementations)
    ParentTestRegistry.register(CategoryA)
    ParentTestRegistry.register(CategoryB)

    yield ParentTestRegistry

    ParentTestRegistry.implementations.clear()
    ParentTestRegistry.implementations.update(original_implementations)
    ParentTestRegistry.clear_cache()


@pytest.fixture
def child_registry(parent_registry):
    """Return ChildTestRegistry with registered implementations."""
    from tests.registries_fixtures import (
        ChildOfA,
        ChildOfB,
        ChildOfBoth,
        ChildTestRegistry,
    )

    original_implementations = dict(ChildTestRegistry.implementations)
    ChildTestRegistry.register(ChildOfA)
    ChildTestRegistry.register(ChildOfB)
    ChildTestRegistry.register(ChildOfBoth)

    yield ChildTestRegistry

    ChildTestRegistry.implementations.clear()
    ChildTestRegistry.implementations.update(original_implementations)
    ChildTestRegistry.clear_cache()


@pytest.fixture
def hierarchical_registry(child_registry):
    """Alias for child_registry for hierarchical tests."""
    return child_registry


@pytest.fixture
def conditional_registry():
    """Return ConditionalTestRegistry with registered implementations."""
    from tests.registries_fixtures import (
        BasicFeature,
        ConditionalTestRegistry,
        PremiumFeature,
    )

    original_implementations = dict(ConditionalTestRegistry.implementations)
    ConditionalTestRegistry.register(PremiumFeature)
    ConditionalTestRegistry.register(BasicFeature)

    yield ConditionalTestRegistry

    ConditionalTestRegistry.implementations.clear()
    ConditionalTestRegistry.implementations.update(original_implementations)
    ConditionalTestRegistry.clear_cache()


@pytest.fixture
def registry_multiple_choice_field(test_strategy_registry):
    """Return a RegistryMultipleChoiceFormField configured with test registry."""
    from django_stratagem.forms import RegistryMultipleChoiceFormField

    return RegistryMultipleChoiceFormField(
        registry=test_strategy_registry,
        choices=test_strategy_registry.get_choices(),
    )


@pytest.fixture
def email_strategy_class():
    """Return EmailStrategy class (not instance)."""
    from tests.registries_fixtures import EmailStrategy

    return EmailStrategy


@pytest.fixture
def admin_site():
    """Return a basic AdminSite instance."""
    from django.contrib.admin import AdminSite

    return AdminSite()


@pytest.fixture
def admin_request():
    """Return a RequestFactory GET request with a superuser attached."""
    from django.contrib.auth import get_user_model
    from django.test import RequestFactory

    User = get_user_model()
    user = User(username="admin", is_staff=True, is_superuser=True)
    request = RequestFactory().get("/admin/")
    request.user = user
    return request


@pytest.fixture
def basic_user():
    """Return a mock user without premium access."""

    class MockUser:
        is_premium = False
        is_authenticated = True

    return MockUser()


@pytest.fixture
def premium_user():
    """Return a mock user with premium access."""

    class MockUser:
        is_premium = True
        is_authenticated = True

    return MockUser()
