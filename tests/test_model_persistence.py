"""Tests for django_stratagem model persistence.

Depends on RegistryFieldTestModel (tests/models.py) which requires a real
database table created by migration 0003_registryfieldtestmodel.
"""

from __future__ import annotations

import pytest

from tests.registries_fixtures import (
    EmailStrategy,
    PushStrategy,
    SMSStrategy,
    TestStrategy,
)
from tests.testapp.models import RegistryFieldTestModel

pytestmark = pytest.mark.django_db


class TestRegistryFieldPersistence:
    """Tests for single RegistryField persistence."""

    def test_save_with_slug(self):
        """Test saving RegistryField with slug value."""
        instance = RegistryFieldTestModel(name="Test 1")
        instance.single_instance = "email"
        instance.save()

        # Reload from database
        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.single_instance is not None
        assert isinstance(reloaded.single_instance, TestStrategy)

    def test_save_with_class(self):
        """Test saving RegistryField with class value."""
        instance = RegistryFieldTestModel(name="Test 2")
        instance.single_instance = EmailStrategy
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.single_instance is not None

    def test_save_with_instance(self):
        """Test saving RegistryField with instance value."""
        instance = RegistryFieldTestModel(name="Test 3")
        instance.single_instance = EmailStrategy()
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.single_instance is not None

    def test_save_with_none(self):
        """Test saving RegistryField with None value."""
        instance = RegistryFieldTestModel(name="Test 4")
        instance.single_instance = None
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.single_instance is None

    def test_update_value(self):
        """Test updating RegistryField value."""
        instance = RegistryFieldTestModel(name="Test 5")
        instance.single_instance = "email"
        instance.save()

        # Update to different value
        instance.single_instance = "sms"
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert isinstance(reloaded.single_instance, SMSStrategy)

    def test_returned_instance_is_callable(self):
        """Test returned instance can execute methods."""
        instance = RegistryFieldTestModel(name="Test 6")
        instance.single_instance = "email"
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        result = reloaded.single_instance.execute()
        assert result == "email_sent"


class TestRegistryClassFieldPersistence:
    """Tests for single RegistryClassField persistence."""

    def test_save_with_slug(self):
        """Test saving RegistryClassField with slug value."""
        instance = RegistryFieldTestModel(name="Class Test 1")
        instance.single_class = "email"
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.single_class is not None
        assert isinstance(reloaded.single_class, type)
        assert issubclass(reloaded.single_class, TestStrategy)

    def test_save_with_class(self):
        """Test saving RegistryClassField with class value."""
        instance = RegistryFieldTestModel(name="Class Test 2")
        instance.single_class = SMSStrategy
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.single_class == SMSStrategy

    def test_returned_class_is_instantiable(self):
        """Test returned class can be instantiated."""
        instance = RegistryFieldTestModel(name="Class Test 3")
        instance.single_class = "push"
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        obj = reloaded.single_class()
        assert isinstance(obj, PushStrategy)
        assert obj.execute() == "push_sent"

    def test_save_with_none(self):
        """Test saving RegistryClassField with None value."""
        instance = RegistryFieldTestModel(name="Class Test 4")
        instance.single_class = None
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.single_class is None


class TestMultipleRegistryFieldPersistence:
    """Tests for MultipleRegistryField persistence."""

    def test_save_with_slug_list(self):
        """Test saving MultipleRegistryField with list of slugs."""
        instance = RegistryFieldTestModel(name="Multi Test 1")
        instance.multiple_instances = ["email", "sms"]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert len(reloaded.multiple_instances) == 2
        for impl in reloaded.multiple_instances:
            assert isinstance(impl, TestStrategy)

    def test_save_with_class_list(self):
        """Test saving MultipleRegistryField with list of classes."""
        instance = RegistryFieldTestModel(name="Multi Test 2")
        instance.multiple_instances = [EmailStrategy, SMSStrategy, PushStrategy]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert len(reloaded.multiple_instances) == 3

    def test_save_with_empty_list(self):
        """Test saving MultipleRegistryField with empty list."""
        instance = RegistryFieldTestModel(name="Multi Test 3")
        instance.multiple_instances = []
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.multiple_instances == []

    def test_returned_instances_are_callable(self):
        """Test all returned instances can execute methods."""
        instance = RegistryFieldTestModel(name="Multi Test 4")
        instance.multiple_instances = ["email", "sms", "push"]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        results = [impl.execute() for impl in reloaded.multiple_instances]
        assert set(results) == {"email_sent", "sms_sent", "push_sent"}

    def test_update_multiple_values(self):
        """Test updating MultipleRegistryField value."""
        instance = RegistryFieldTestModel(name="Multi Test 5")
        instance.multiple_instances = ["email"]
        instance.save()

        # Update to different list
        instance.multiple_instances = ["sms", "push"]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert len(reloaded.multiple_instances) == 2


class TestMultipleRegistryClassFieldPersistence:
    """Tests for MultipleRegistryClassField persistence."""

    def test_save_with_slug_list(self):
        """Test saving MultipleRegistryClassField with list of slugs."""
        instance = RegistryFieldTestModel(name="MultiClass Test 1")
        instance.multiple_classes = ["email", "push"]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert len(reloaded.multiple_classes) == 2
        for cls in reloaded.multiple_classes:
            assert isinstance(cls, type)
            assert issubclass(cls, TestStrategy)

    def test_save_with_class_list(self):
        """Test saving MultipleRegistryClassField with list of classes."""
        instance = RegistryFieldTestModel(name="MultiClass Test 2")
        instance.multiple_classes = [EmailStrategy, SMSStrategy]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert set(reloaded.multiple_classes) == {EmailStrategy, SMSStrategy}

    def test_returned_classes_are_instantiable(self):
        """Test all returned classes can be instantiated."""
        instance = RegistryFieldTestModel(name="MultiClass Test 3")
        instance.multiple_classes = ["email", "sms"]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        for cls in reloaded.multiple_classes:
            obj = cls()
            assert isinstance(obj, TestStrategy)

    def test_save_with_empty_list(self):
        """Test saving MultipleRegistryClassField with empty list."""
        instance = RegistryFieldTestModel(name="MultiClass Test 4")
        instance.multiple_classes = []
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert reloaded.multiple_classes == []


class TestCombinedFieldPersistence:
    """Tests for saving multiple field types together."""

    def test_save_all_field_types(self):
        """Test saving all field types on one model."""
        instance = RegistryFieldTestModel(name="Combined Test")
        instance.single_instance = "email"
        instance.single_class = "sms"
        instance.multiple_instances = ["email", "push"]
        instance.multiple_classes = ["sms", "push"]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)

        # Verify single instance
        assert isinstance(reloaded.single_instance, TestStrategy)

        # Verify single class
        assert isinstance(reloaded.single_class, type)

        # Verify multiple instances
        assert len(reloaded.multiple_instances) == 2

        # Verify multiple classes
        assert len(reloaded.multiple_classes) == 2

    def test_partial_field_values(self):
        """Test saving with some fields None/empty."""
        instance = RegistryFieldTestModel(name="Partial Test")
        instance.single_instance = "email"
        instance.single_class = None
        instance.multiple_instances = []
        instance.multiple_classes = ["sms"]
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)

        assert reloaded.single_instance is not None
        assert reloaded.single_class is None
        assert reloaded.multiple_instances == []
        assert len(reloaded.multiple_classes) == 1


class TestQuerySetFiltering:
    """Tests for QuerySet filtering with registry fields."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Create test data for filtering tests."""
        RegistryFieldTestModel.objects.create(
            name="Email Only",
            single_instance="email",
        )
        RegistryFieldTestModel.objects.create(
            name="SMS Only",
            single_instance="sms",
        )
        RegistryFieldTestModel.objects.create(
            name="Push Only",
            single_instance="push",
        )

    def test_filter_by_slug(self):
        """Test filtering by slug value."""
        results = RegistryFieldTestModel.objects.filter(single_instance="email")
        assert results.count() == 1
        assert results.first().name == "Email Only"

    def test_filter_excludes_non_matching(self):
        """Test filtering excludes non-matching records."""
        results = RegistryFieldTestModel.objects.exclude(single_instance="email")
        assert results.count() == 2

    def test_filter_with_none(self):
        """Test filtering for None values."""
        RegistryFieldTestModel.objects.create(
            name="No Instance",
            single_instance=None,
        )
        results = RegistryFieldTestModel.objects.filter(single_instance__isnull=True)
        assert results.count() == 1
        assert results.first().name == "No Instance"


class TestPersistenceEdgeCases:
    """Tests for edge cases in model persistence."""

    def test_create_with_defaults(self):
        """Test creating model with default values."""
        instance = RegistryFieldTestModel.objects.create(name="Defaults Test")
        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        # Default values should be None/empty
        assert reloaded.single_instance is None
        assert reloaded.single_class is None

    def test_bulk_create(self):
        """Test bulk creating models with registry fields."""
        instances = [
            RegistryFieldTestModel(name="Bulk 1", single_instance="email"),
            RegistryFieldTestModel(name="Bulk 2", single_instance="sms"),
            RegistryFieldTestModel(name="Bulk 3", single_instance="push"),
        ]
        RegistryFieldTestModel.objects.bulk_create(instances)

        assert RegistryFieldTestModel.objects.filter(name__startswith="Bulk").count() == 3

    def test_update_via_queryset(self):
        """Test updating via QuerySet.update()."""
        instance = RegistryFieldTestModel.objects.create(
            name="Update Test",
            single_instance="email",
        )

        # Update via QuerySet - note: this updates raw DB value
        RegistryFieldTestModel.objects.filter(pk=instance.pk).update(single_instance="sms")

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        # After raw update, the value should still be accessible
        assert isinstance(reloaded.single_instance, SMSStrategy)

    def test_str_representation(self):
        """Test model string representation."""
        instance = RegistryFieldTestModel.objects.create(
            name="Str Test",
            single_instance="email",
        )
        str_repr = str(instance)
        assert "Str Test" in str_repr
        assert str(instance.pk) in str_repr

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("single_instance", "email"),
            ("single_instance", "sms"),
            ("single_instance", "push"),
            ("single_class", "email"),
            ("single_class", "sms"),
        ],
    )
    def test_various_slug_values(self, field_name, value):
        """Test persistence with various valid slug values."""
        instance = RegistryFieldTestModel(name=f"Test {field_name} {value}")
        setattr(instance, field_name, value)
        instance.save()

        reloaded = RegistryFieldTestModel.objects.get(pk=instance.pk)
        assert getattr(reloaded, field_name) is not None
