"""Tests for django_stratagem lookups module.

Depends on RegistryFieldTestModel (tests/models.py) which requires a real
database table created by migration 0003_registryfieldtestmodel.
"""

from __future__ import annotations

import pytest

from tests.registries_fixtures import EmailStrategy
from tests.testapp.models import RegistryFieldTestModel

pytestmark = pytest.mark.django_db


class TestRegistryFieldLookupMixin:
    """Tests for RegistryFieldLookupMixin.get_prep_lookup behavior."""

    def test_string_value_passed_through(self):
        """Test string values are passed through unchanged."""
        # Create test data
        instance = RegistryFieldTestModel.objects.create(
            name="Test",
            single_instance="email",
        )

        # Query with string
        result = RegistryFieldTestModel.objects.filter(single_instance="email")
        assert result.count() == 1
        assert result.first().pk == instance.pk

    def test_class_converted_to_fqn(self):
        """Test class values are converted to fully qualified name."""
        RegistryFieldTestModel.objects.create(
            name="Test",
            single_instance="email",
        )

        # Query with class - this tests the lookup conversion
        result = RegistryFieldTestModel.objects.filter(single_instance=EmailStrategy)
        assert result.count() == 1
        assert result.first().name == "Test"

    def test_instance_converted_to_class_fqn(self):
        """Test instance values use class FQN."""
        RegistryFieldTestModel.objects.create(
            name="Test",
            single_instance="email",
        )

        # Query with instance
        email_instance = EmailStrategy()
        result = RegistryFieldTestModel.objects.filter(single_instance=email_instance)
        assert result.count() == 1
        assert result.first().name == "Test"

    def test_list_value_converted_to_string_via_lookup(self):
        """Test list values are converted via stringify in get_prep_lookup."""
        from unittest.mock import MagicMock

        from django_stratagem.lookups import RegistryFieldExact

        lhs = MagicMock()
        lhs.output_field.get_prep_value.side_effect = lambda x: x

        lookup = RegistryFieldExact(lhs, ["email", "sms"])
        result = lookup.get_prep_lookup()
        assert isinstance(result, str)
        assert "," in result

    def test_class_value_converted_to_fqn_via_lookup(self):
        """Test class values are converted to FQN in get_prep_lookup."""
        from unittest.mock import MagicMock

        from django_stratagem.lookups import RegistryFieldExact

        lhs = MagicMock()
        lhs.output_field.get_prep_value.side_effect = lambda x: x

        lookup = RegistryFieldExact(lhs, EmailStrategy)
        result = lookup.get_prep_lookup()
        expected = f"{EmailStrategy.__module__}.{EmailStrategy.__name__}"
        assert result == expected

    def test_instance_value_uses_class_fqn_via_lookup(self):
        """Test instance values use class FQN in get_prep_lookup."""
        from unittest.mock import MagicMock

        from django_stratagem.lookups import RegistryFieldExact

        lhs = MagicMock()
        lhs.output_field.get_prep_value.side_effect = lambda x: x

        instance = EmailStrategy()
        lookup = RegistryFieldExact(lhs, instance)
        result = lookup.get_prep_lookup()
        expected = f"{EmailStrategy.__module__}.{EmailStrategy.__name__}"
        assert result == expected

    def test_none_value_handled(self):
        """Test None values are handled correctly."""
        RegistryFieldTestModel.objects.create(
            name="With Value",
            single_instance="email",
        )
        RegistryFieldTestModel.objects.create(
            name="Without Value",
            single_instance=None,
        )

        # Query for None
        result = RegistryFieldTestModel.objects.filter(single_instance__isnull=True)
        assert result.count() == 1
        assert result.first().name == "Without Value"


class TestExactLookup:
    """Tests for exact lookup on registry fields."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Create test data."""
        RegistryFieldTestModel.objects.create(name="Email", single_instance="email")
        RegistryFieldTestModel.objects.create(name="SMS", single_instance="sms")
        RegistryFieldTestModel.objects.create(name="Push", single_instance="push")

    def test_exact_match_with_slug(self):
        """Test exact match with slug."""
        result = RegistryFieldTestModel.objects.filter(single_instance__exact="email")
        assert result.count() == 1
        assert result.first().name == "Email"

    def test_exact_no_match(self):
        """Test exact lookup returns empty for non-matching value."""
        result = RegistryFieldTestModel.objects.filter(single_instance__exact="invalid")
        assert result.count() == 0

    def test_exact_with_slug_shorthand(self):
        """Test exact lookup via field=value (implicit exact)."""
        result = RegistryFieldTestModel.objects.filter(single_instance="sms")
        assert result.count() == 1
        assert result.first().name == "SMS"


class TestIExactLookup:
    """Tests for case-insensitive exact lookup.

    Note: The database stores fully qualified names (FQN), not slugs.
    So iexact lookups must use the FQN or a substring that matches.
    Slug-based lookups won't work because the stored value is the FQN.
    """

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Create test data."""
        RegistryFieldTestModel.objects.create(name="Email", single_instance="email")

    def test_iexact_with_fqn(self):
        """Test iexact with fully qualified name."""
        fqn = f"{EmailStrategy.__module__}.{EmailStrategy.__name__}"
        result = RegistryFieldTestModel.objects.filter(single_instance__iexact=fqn)
        assert result.count() == 1

    def test_iexact_with_fqn_uppercase(self):
        """Test iexact with uppercase FQN (should match case-insensitively)."""
        fqn = f"{EmailStrategy.__module__}.{EmailStrategy.__name__}".upper()
        result = RegistryFieldTestModel.objects.filter(single_instance__iexact=fqn)
        assert result.count() == 1

    def test_iexact_with_fqn_mixed_case(self):
        """Test iexact with mixed case FQN."""
        fqn = f"{EmailStrategy.__module__}.{EmailStrategy.__name__}"
        mixed = fqn[: len(fqn) // 2].upper() + fqn[len(fqn) // 2 :].lower()
        result = RegistryFieldTestModel.objects.filter(single_instance__iexact=mixed)
        assert result.count() == 1

    def test_iexact_with_slug_returns_empty(self):
        """Test iexact with slug returns empty (slugs aren't converted to FQN in lookups).

        Note: This documents current behavior. Slug-based lookups don't work
        because the lookup doesn't convert slugs to FQN before comparison.
        """
        result = RegistryFieldTestModel.objects.filter(single_instance__iexact="email")
        # Current behavior: returns empty because DB stores FQN, not slug
        assert result.count() == 0


class TestContainsLookup:
    """Tests for contains lookup on registry fields.

    Note: The database stores fully qualified names (FQN), so contains
    lookups will match substrings of the FQN (e.g., class name or module name).
    """

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Create test data."""
        RegistryFieldTestModel.objects.create(name="Email", single_instance="email")
        RegistryFieldTestModel.objects.create(name="SMS", single_instance="sms")

    def test_contains_class_name(self):
        """Test contains finds match by class name substring."""
        # FQN contains "EmailStrategy", so "Email" should match
        result = RegistryFieldTestModel.objects.filter(single_instance__contains="EmailStrategy")
        assert result.count() == 1
        assert result.first().name == "Email"

    def test_contains_module_name(self):
        """Test contains finds match by module name substring."""
        # FQN contains the module path
        result = RegistryFieldTestModel.objects.filter(single_instance__contains="registries_fixtures")
        # Should match both Email and SMS since both are in same module
        assert result.count() == 2

    def test_contains_no_match(self):
        """Test contains returns empty for no match."""
        result = RegistryFieldTestModel.objects.filter(single_instance__contains="invalid_xyz_not_found")
        assert result.count() == 0

    def test_contains_slug_matches_if_in_fqn(self):
        """Test contains with slug that happens to be in FQN.

        The FQN is "tests.registries_fixtures.EmailStrategy".
        On SQLite, LIKE is case-insensitive for ASCII, so "email" matches
        "Email" in "EmailStrategy". On PostgreSQL, this would be case-sensitive
        and would NOT match.
        """
        result = RegistryFieldTestModel.objects.filter(single_instance__contains="email")
        # On SQLite (used in tests), LIKE is case-insensitive so this matches
        assert result.count() == 1


class TestIContainsLookup:
    """Tests for case-insensitive contains lookup."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Create test data."""
        RegistryFieldTestModel.objects.create(name="Email", single_instance="email")

    def test_icontains_lowercase(self):
        """Test icontains with lowercase pattern."""
        result = RegistryFieldTestModel.objects.filter(single_instance__icontains="mail")
        assert result.count() == 1

    def test_icontains_uppercase(self):
        """Test icontains with uppercase pattern."""
        result = RegistryFieldTestModel.objects.filter(single_instance__icontains="MAIL")
        assert result.count() == 1

    def test_icontains_mixed_case(self):
        """Test icontains with mixed case pattern."""
        result = RegistryFieldTestModel.objects.filter(single_instance__icontains="Mail")
        assert result.count() == 1


class TestMultipleFieldLookups:
    """Tests for lookups on multiple registry fields.

    Note: Multiple field stores FQNs as comma-separated string.
    """

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Create test data."""
        RegistryFieldTestModel.objects.create(
            name="Email and SMS",
            multiple_instances=["email", "sms"],
        )
        RegistryFieldTestModel.objects.create(
            name="Push Only",
            multiple_instances=["push"],
        )
        RegistryFieldTestModel.objects.create(
            name="All Three",
            multiple_instances=["email", "sms", "push"],
        )

    def test_contains_on_multiple_field_by_class_name(self):
        """Test contains lookup on multiple registry field using class name.

        Note: The multiple_instances field may be nullable or have different storage.
        This test documents current behavior - queries may return 0 results if
        the field is stored differently than expected.
        """
        # Multiple field stores comma-separated FQNs
        # Search for class name substring
        result = RegistryFieldTestModel.objects.filter(multiple_instances__contains="EmailStrategy")
        # "Email and SMS" and "All Three" both contain EmailStrategy FQN
        assert result.count() == 2

    def test_contains_on_multiple_field_by_module(self):
        """Test contains lookup on multiple registry field using module name.

        Note: This test documents current behavior. The field may store
        data differently or may be nullable, resulting in fewer matches.
        """
        result = RegistryFieldTestModel.objects.filter(multiple_instances__contains="registries_fixtures")
        # All three records contain FQNs from tests.registries_fixtures
        assert result.count() == 3

    def test_multiple_field_exact_match(self):
        """Test exact match on multiple field uses stored FQN value."""
        push_only = RegistryFieldTestModel.objects.get(name="Push Only")
        # Get the raw stored value and verify exact match retrieves the same record
        raw_value = RegistryFieldTestModel.objects.filter(pk=push_only.pk).values_list(
            "multiple_instances", flat=True
        )[0]
        result = RegistryFieldTestModel.objects.filter(multiple_instances__exact=raw_value)
        assert result.count() == 1
        assert result.first().name == "Push Only"


class TestRegistryClassFieldLookups:
    """Tests for lookups on RegistryClassField."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Create test data."""
        RegistryFieldTestModel.objects.create(name="Email Class", single_class="email")
        RegistryFieldTestModel.objects.create(name="SMS Class", single_class="sms")

    def test_exact_on_class_field(self):
        """Test exact lookup on class field."""
        result = RegistryFieldTestModel.objects.filter(single_class__exact="email")
        assert result.count() == 1
        assert result.first().name == "Email Class"

    def test_contains_on_class_field(self):
        """Test contains lookup on class field."""
        result = RegistryFieldTestModel.objects.filter(single_class__contains="mail")
        assert result.count() == 1


class TestLookupEdgeCases:
    """Tests for edge cases in lookups."""

    def test_lookup_with_empty_database(self):
        """Test lookups work with empty database."""
        result = RegistryFieldTestModel.objects.filter(single_instance="email")
        assert result.count() == 0

    def test_chained_lookups(self):
        """Test multiple lookups can be chained."""
        RegistryFieldTestModel.objects.create(
            name="Test",
            single_instance="email",
            single_class="sms",
        )

        result = RegistryFieldTestModel.objects.filter(
            single_instance="email",
            single_class="sms",
        )
        assert result.count() == 1

    def test_exclude_with_lookup(self):
        """Test exclude with registry field lookup."""
        RegistryFieldTestModel.objects.create(name="Email", single_instance="email")
        RegistryFieldTestModel.objects.create(name="SMS", single_instance="sms")

        result = RegistryFieldTestModel.objects.exclude(single_instance="email")
        assert result.count() == 1
        assert result.first().name == "SMS"

    def test_or_query_with_lookups(self):
        """Test OR query with registry field lookups."""
        from django.db.models import Q

        RegistryFieldTestModel.objects.create(name="Email", single_instance="email")
        RegistryFieldTestModel.objects.create(name="SMS", single_instance="sms")
        RegistryFieldTestModel.objects.create(name="Push", single_instance="push")

        result = RegistryFieldTestModel.objects.filter(Q(single_instance="email") | Q(single_instance="sms"))
        assert result.count() == 2

    @pytest.mark.parametrize(
        "lookup_suffix,value",
        [
            # exact and iexact work with the slug because exact lookup is identity
            ("exact", "email"),  # Works because we stored "email" which gets converted to FQN internally
            # For iexact, contains, icontains - use class name since DB stores FQN
            ("iexact", f"{EmailStrategy.__module__}.{EmailStrategy.__name__}"),
            ("contains", "EmailStrategy"),
            ("icontains", "emailstrategy"),
        ],
    )
    def test_all_lookup_types(self, lookup_suffix, value):
        """Test all lookup types work with appropriate values.

        Note: exact works with slug because the field converts it.
        Other lookups need FQN-compatible values since DB stores FQN.
        """
        RegistryFieldTestModel.objects.create(name="Email", single_instance="email")

        lookup_key = f"single_instance__{lookup_suffix}"
        result = RegistryFieldTestModel.objects.filter(**{lookup_key: value})
        assert result.count() == 1
