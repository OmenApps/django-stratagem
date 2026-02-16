"""Tests for django_stratagem widgets module."""

from __future__ import annotations

import pytest
from django.forms import Select

from django_stratagem.widgets import HierarchicalRegistryWidget, RegistryWidget


class TestRegistryWidget:
    """Tests for RegistryWidget."""

    def test_inherits_from_select(self):
        """Test widget inherits from Select."""
        widget = RegistryWidget()
        assert isinstance(widget, Select)

    def test_init_stores_registry(self, test_registry):
        """Test __init__ stores the registry attribute."""
        widget = RegistryWidget(registry=test_registry)
        assert widget.registry is test_registry

    def test_init_without_registry(self):
        """Test __init__ defaults registry to None."""
        widget = RegistryWidget()
        assert widget.registry is None

    def test_create_option_with_description(self, test_registry):
        """Test create_option sets title attr from meta description."""
        widget = RegistryWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        option = widget.create_option("field", "email", "Email Strategy", False, 0)
        assert option["attrs"]["title"] == "Send notifications via email"

    def test_create_option_with_icon(self, test_registry):
        """Test create_option sets data-icon attr from meta icon."""
        widget = RegistryWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        option = widget.create_option("field", "email", "Email Strategy", False, 0)
        assert option["attrs"]["data-icon"] == "fa-solid fa-envelope"

    def test_create_option_with_priority(self, test_registry):
        """Test create_option sets data-priority attr from meta priority."""
        widget = RegistryWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        option = widget.create_option("field", "email", "Email Strategy", False, 0)
        assert option["attrs"]["data-priority"] == "10"

    def test_create_option_with_all_meta(self, test_registry):
        """Test create_option sets all three attrs when meta has all fields."""
        widget = RegistryWidget(
            choices=[("sms", "SMS Strategy")],
            registry=test_registry,
        )
        option = widget.create_option("field", "sms", "SMS Strategy", False, 0)
        assert option["attrs"]["title"] == "Send notifications via SMS"
        assert option["attrs"]["data-icon"] == "fa-solid fa-message"
        assert option["attrs"]["data-priority"] == "20"

    def test_create_option_without_registry(self):
        """Test create_option does not enrich when no registry."""
        widget = RegistryWidget(choices=[("email", "Email")])
        option = widget.create_option("field", "email", "Email", False, 0)
        assert "title" not in option["attrs"]
        assert "data-icon" not in option["attrs"]
        assert "data-priority" not in option["attrs"]

    def test_create_option_with_empty_value(self, test_registry):
        """Test create_option does not enrich when value is empty string."""
        widget = RegistryWidget(
            choices=[("", "---")],
            registry=test_registry,
        )
        option = widget.create_option("field", "", "---", False, 0)
        assert "title" not in option["attrs"]
        assert "data-icon" not in option["attrs"]

    def test_create_option_value_not_in_registry(self, test_registry):
        """Test create_option does not enrich when value not in implementations."""
        widget = RegistryWidget(
            choices=[("nonexistent", "Missing")],
            registry=test_registry,
        )
        option = widget.create_option("field", "nonexistent", "Missing", False, 0)
        assert "title" not in option["attrs"]
        assert "data-icon" not in option["attrs"]

    def test_create_option_meta_partial_fields(self, test_registry):
        """Test create_option handles meta with only some fields populated."""
        from tests.registries_fixtures import TestStrategy, TestStrategyRegistry

        class MinimalStrategy(TestStrategy):
            slug = "minimal"
            display_name = "Minimal"
            description = "Has description only"
            # No icon or priority set (inherited defaults are empty/0)

        TestStrategyRegistry.register(MinimalStrategy)
        widget = RegistryWidget(
            choices=[("minimal", "Minimal")],
            registry=TestStrategyRegistry,
        )
        option = widget.create_option("field", "minimal", "Minimal", False, 0)
        assert option["attrs"]["title"] == "Has description only"
        assert "data-icon" not in option["attrs"]
        assert "data-priority" not in option["attrs"]

    def test_render_produces_enriched_html(self, test_registry):
        """Integration test: full render produces HTML with enriched attrs."""
        widget = RegistryWidget(
            choices=[("email", "Email Strategy"), ("sms", "SMS Strategy")],
            registry=test_registry,
        )
        html = widget.render("notification_type", "email")
        assert 'title="Send notifications via email"' in html
        assert "data-icon" in html


class TestHierarchicalRegistryWidget:
    """Tests for HierarchicalRegistryWidget."""

    def test_inherits_from_select(self):
        """Test widget inherits from Select."""
        widget = HierarchicalRegistryWidget()
        assert isinstance(widget, Select)

    def test_init_without_parent_field(self):
        """Test initialization without parent_field."""
        widget = HierarchicalRegistryWidget()
        assert widget.parent_field is None

    def test_init_with_parent_field(self):
        """Test initialization with parent_field."""
        widget = HierarchicalRegistryWidget(parent_field="category")
        assert widget.parent_field == "category"

    def test_init_with_choices(self):
        """Test initialization with choices."""
        choices = [("a", "Choice A"), ("b", "Choice B")]
        widget = HierarchicalRegistryWidget(choices=choices)
        assert list(widget.choices) == choices

    def test_init_with_attrs(self):
        """Test initialization with custom attrs."""
        attrs = {"class": "custom-class", "id": "my-widget"}
        widget = HierarchicalRegistryWidget(attrs=attrs)
        assert widget.attrs.get("class") == "custom-class"
        assert widget.attrs.get("id") == "my-widget"

    def test_render_without_parent_field(self):
        """Test render doesn't add data attributes without parent_field."""
        widget = HierarchicalRegistryWidget(choices=[("a", "A")])
        html = widget.render("test_field", "a")

        assert "data-parent-field" not in html
        assert "data-hierarchical" not in html

    def test_render_with_parent_field(self):
        """Test render adds data attributes with parent_field."""
        widget = HierarchicalRegistryWidget(
            choices=[("a", "A")],
            parent_field="parent_category",
        )
        html = widget.render("test_field", "a")

        assert 'data-parent-field="parent_category"' in html
        assert 'data-hierarchical="true"' in html

    def test_render_preserves_existing_attrs(self):
        """Test render preserves attrs passed to render method."""
        widget = HierarchicalRegistryWidget(
            choices=[("a", "A")],
            parent_field="parent",
        )
        html = widget.render("test_field", "a", attrs={"class": "my-class"})

        assert "my-class" in html
        assert "data-parent-field" in html

    def test_render_with_none_attrs(self):
        """Test render handles None attrs parameter."""
        widget = HierarchicalRegistryWidget(
            choices=[("a", "A")],
            parent_field="parent",
        )
        html = widget.render("test_field", "a", attrs=None)

        assert "data-parent-field" in html

    def test_render_with_empty_attrs(self):
        """Test render handles empty attrs dict."""
        widget = HierarchicalRegistryWidget(
            choices=[("a", "A")],
            parent_field="parent",
        )
        html = widget.render("test_field", "a", attrs={})

        assert "data-parent-field" in html

    def test_render_includes_name(self):
        """Test rendered HTML includes field name."""
        widget = HierarchicalRegistryWidget(choices=[("a", "A")])
        html = widget.render("my_field_name", "a")

        assert "my_field_name" in html

    def test_render_includes_value(self):
        """Test rendered HTML selects the correct value."""
        widget = HierarchicalRegistryWidget(choices=[("a", "Choice A"), ("b", "Choice B")])
        html = widget.render("test_field", "b")

        # The 'selected' attribute should be on option b
        assert "selected" in html

    def test_render_with_renderer(self):
        """Test render accepts renderer parameter."""
        widget = HierarchicalRegistryWidget(choices=[("a", "A")])
        # Should not raise
        html = widget.render("test_field", "a", renderer=None)
        assert html is not None


class TestHierarchicalRegistryWidgetEdgeCases:
    """Tests for edge cases in HierarchicalRegistryWidget."""

    def test_empty_choices(self):
        """Test widget with empty choices."""
        widget = HierarchicalRegistryWidget(choices=[])
        html = widget.render("test_field", None)
        assert "select" in html.lower()

    def test_none_value(self):
        """Test render with None value."""
        widget = HierarchicalRegistryWidget(choices=[("a", "A")])
        html = widget.render("test_field", None)
        assert html is not None

    def test_empty_string_value(self):
        """Test render with empty string value."""
        widget = HierarchicalRegistryWidget(choices=[("", "---"), ("a", "A")])
        html = widget.render("test_field", "")
        assert html is not None

    @pytest.mark.parametrize(
        "parent_field",
        [
            "simple_name",
            "field_with_underscore",
            "CamelCaseName",
            "field123",
        ],
    )
    def test_various_parent_field_names(self, parent_field):
        """Test widget handles various parent field name formats."""
        widget = HierarchicalRegistryWidget(
            choices=[("a", "A")],
            parent_field=parent_field,
        )
        html = widget.render("test_field", "a")
        assert f'data-parent-field="{parent_field}"' in html

    def test_special_characters_in_choices(self):
        """Test widget handles special characters in choices."""
        choices = [
            ("special<>&", "Choice with <special> chars"),
            ("unicode_", "Choice"),
        ]
        widget = HierarchicalRegistryWidget(choices=choices)
        html = widget.render("test_field", None)
        # Should escape HTML properly
        assert html is not None

    def test_widget_can_be_reused(self):
        """Test widget can render multiple times."""
        widget = HierarchicalRegistryWidget(
            choices=[("a", "A"), ("b", "B")],
            parent_field="parent",
        )

        html1 = widget.render("field1", "a")
        html2 = widget.render("field2", "b")

        assert "field1" in html1
        assert "field2" in html2

    def test_attrs_not_mutated_between_renders(self):
        """Test rendering doesn't permanently mutate widget attrs."""
        widget = HierarchicalRegistryWidget(
            choices=[("a", "A")],
            parent_field="parent",
            attrs={"class": "original"},
        )

        # First render with extra attrs
        widget.render("field1", "a", attrs={"id": "field1"})

        # Widget's original attrs should be unchanged
        assert widget.attrs.get("class") == "original"
