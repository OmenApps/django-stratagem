"""Tests for django_stratagem widgets module."""

from __future__ import annotations

import pytest
from django.forms import Select

from django_stratagem.widgets import HierarchicalRegistryWidget, RegistryDescriptionWidget, RegistryWidget


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

    def test_create_option_adds_data_description(self, test_registry):
        """Test create_option sets data-description attr from meta description."""
        widget = RegistryWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        option = widget.create_option("field", "email", "Email Strategy", False, 0)
        assert option["attrs"]["data-description"] == "Send notifications via email"

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
        assert option["attrs"]["data-description"] == "Send notifications via SMS"
        assert option["attrs"]["data-icon"] == "fa-solid fa-message"
        assert option["attrs"]["data-priority"] == "20"

    def test_create_option_without_registry(self):
        """Test create_option does not enrich when no registry."""
        widget = RegistryWidget(choices=[("email", "Email")])
        option = widget.create_option("field", "email", "Email", False, 0)
        assert "title" not in option["attrs"]
        assert "data-description" not in option["attrs"]
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
        assert "data-description" not in option["attrs"]
        assert "data-icon" not in option["attrs"]

    def test_create_option_value_not_in_registry(self, test_registry):
        """Test create_option does not enrich when value not in implementations."""
        widget = RegistryWidget(
            choices=[("nonexistent", "Missing")],
            registry=test_registry,
        )
        option = widget.create_option("field", "nonexistent", "Missing", False, 0)
        assert "title" not in option["attrs"]
        assert "data-description" not in option["attrs"]
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
        assert option["attrs"]["data-description"] == "Has description only"
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
        assert "data-description" in html


class TestRegistryDescriptionWidget:
    """Tests for RegistryDescriptionWidget."""

    def test_inherits_from_registry_widget(self):
        """Test widget inherits from RegistryWidget."""
        widget = RegistryDescriptionWidget()
        assert isinstance(widget, RegistryWidget)
        assert isinstance(widget, Select)

    def test_template_name_set(self):
        """Test the custom template_name is set."""
        widget = RegistryDescriptionWidget()
        assert widget.template_name == "django_stratagem/widgets/registry_description_select.html"

    def test_media_includes_js(self):
        """Test the widget's Media class includes the JS file."""
        widget = RegistryDescriptionWidget()
        assert "django_stratagem/js/registry_description.js" in widget.media._js

    def test_init_default_description_attrs(self):
        """Test __init__ defaults description_attrs to empty dict."""
        widget = RegistryDescriptionWidget()
        assert widget.description_attrs == {}

    def test_init_custom_description_attrs(self):
        """Test __init__ stores custom description_attrs."""
        attrs = {"class": "card bg-light", "style": "padding: 1rem;"}
        widget = RegistryDescriptionWidget(description_attrs=attrs)
        assert widget.description_attrs == attrs

    def test_init_stores_registry(self, test_registry):
        """Test __init__ stores the registry attribute."""
        widget = RegistryDescriptionWidget(registry=test_registry)
        assert widget.registry is test_registry

    def test_get_context_includes_description_attrs(self, test_registry):
        """Test get_context adds description_attrs to widget context."""
        desc_attrs = {"class": "my-class", "style": "color: red;"}
        widget = RegistryDescriptionWidget(
            choices=[("email", "Email")],
            registry=test_registry,
            description_attrs=desc_attrs,
        )
        context = widget.get_context("test_field", "email", {"id": "id_test_field"})
        assert context["widget"]["description_attrs"] == desc_attrs

    def test_render_includes_select_and_description_container(self, test_registry):
        """Test render produces both the select and the description container div."""
        widget = RegistryDescriptionWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        html = widget.render("backend", "email", attrs={"id": "id_backend"})
        # Should contain a <select> element
        assert "<select" in html
        # Should contain the description container
        assert 'data-registry-description-for="id_backend"' in html
        assert "registry-description-container" in html

    def test_render_description_container_has_correct_id(self, test_registry):
        """Test the description container's id is based on the select's id."""
        widget = RegistryDescriptionWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        html = widget.render("backend", "email", attrs={"id": "id_backend"})
        assert 'id="id_backend-registry-description"' in html

    def test_render_options_have_data_description(self, test_registry):
        """Test rendered options have data-description attributes."""
        widget = RegistryDescriptionWidget(
            choices=[("email", "Email Strategy"), ("sms", "SMS Strategy")],
            registry=test_registry,
        )
        html = widget.render("backend", "email", attrs={"id": "id_backend"})
        assert 'data-description="Send notifications via email"' in html
        assert 'data-description="Send notifications via SMS"' in html

    def test_render_blank_option_no_data_description(self, test_registry):
        """Test blank option does not get a data-description attribute."""
        widget = RegistryDescriptionWidget(
            choices=[("", "---"), ("email", "Email Strategy")],
            registry=test_registry,
        )
        html = widget.render("backend", "", attrs={"id": "id_backend"})
        # The blank option should not have data-description
        # Count occurrences: only the email option should have it
        assert html.count("data-description=") == 1

    def test_render_with_custom_description_attrs(self, test_registry):
        """Test render applies custom description_attrs to the container."""
        widget = RegistryDescriptionWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
            description_attrs={"class": "card bg-light mb-3", "style": "padding: 1rem;"},
        )
        html = widget.render("backend", "email", attrs={"id": "id_backend"})
        assert "card bg-light mb-3" in html
        assert "padding: 1rem;" in html

    def test_render_description_container_has_aria_live(self, test_registry):
        """Test the description container has aria-live for accessibility."""
        widget = RegistryDescriptionWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        html = widget.render("backend", "email", attrs={"id": "id_backend"})
        assert 'aria-live="polite"' in html
        assert 'aria-atomic="true"' in html

    def test_render_default_style(self, test_registry):
        """Test the description container has default margin-top style."""
        widget = RegistryDescriptionWidget(
            choices=[("email", "Email Strategy")],
            registry=test_registry,
        )
        html = widget.render("backend", "email", attrs={"id": "id_backend"})
        assert "margin-top: 0.25rem;" in html


class TestFormfieldShowDescription:
    """Tests for the show_description parameter on formfield()."""

    def test_formfield_with_show_description_uses_description_widget(self):
        """Test formfield() with show_description=True returns RegistryDescriptionWidget."""
        from tests.testapp.models import RegistryFieldTestModel

        field = RegistryFieldTestModel._meta.get_field("single_instance")
        form_field = field.formfield(show_description=True)
        assert isinstance(form_field.widget, RegistryDescriptionWidget)

    def test_formfield_without_show_description_uses_default(self):
        """Test formfield() without show_description uses the default widget."""
        from tests.testapp.models import RegistryFieldTestModel

        field = RegistryFieldTestModel._meta.get_field("single_instance")
        form_field = field.formfield()
        assert not isinstance(form_field.widget, RegistryDescriptionWidget)

    def test_formfield_show_description_does_not_override_explicit_widget(self):
        """Test show_description is ignored when an explicit widget is passed."""
        from tests.testapp.models import RegistryFieldTestModel

        field = RegistryFieldTestModel._meta.get_field("single_instance")
        form_field = field.formfield(show_description=True, widget=RegistryWidget)
        # Check type, not identity, in case Django does a deepcopy of the widget
        assert type(form_field.widget) is RegistryWidget
        assert not isinstance(form_field.widget, RegistryDescriptionWidget)


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
