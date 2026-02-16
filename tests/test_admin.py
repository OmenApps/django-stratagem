"""Tests for django_stratagem admin module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory

from django_stratagem.admin import (
    ContextAwareRegistryAdmin,
    DjangoStratagemAdminSite,
    EnhancedDjangoStratagemAdminSite,
    HierarchicalRegistryAdmin,
    RegistryFieldListFilter,
    RegistryListMixin,
)
from django_stratagem.fields import AbstractRegistryField
from django_stratagem.forms import ContextAwareRegistryFormField

pytestmark = pytest.mark.django_db


class MockChangeList:
    """Mock ChangeList for admin filter tests."""

    def get_query_string(self, new_params=None, remove=None):
        params = {}
        if new_params:
            params.update(new_params)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"?{query}" if query else "?"


@pytest.fixture
def superuser():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User(username="admin", is_staff=True, is_superuser=True)


@pytest.fixture
def admin_rf(superuser):
    """Return a request factory with a superuser-attached request."""
    factory = RequestFactory()
    request = factory.get("/admin/")
    request.user = superuser
    return request


def _make_mock_filter(registry, request):
    """Create a mock RegistryFieldListFilter without calling __init__."""
    filter_obj = object.__new__(RegistryFieldListFilter)
    field = MagicMock(spec=AbstractRegistryField)
    field.registry = registry
    field.name = "test_field"
    filter_obj.field = field
    filter_obj.request = request
    filter_obj.lookup_val = None
    filter_obj.lookup_kwarg = "test_field__exact"
    filter_obj.lookup_kwarg_isnull = "test_field__isnull"
    return filter_obj


class TestRegistryFieldListFilter:
    """Tests for RegistryFieldListFilter."""

    def test_choices_yields_all_option(self, test_strategy_registry, admin_rf):
        filter_obj = _make_mock_filter(test_strategy_registry, admin_rf)
        changelist = MockChangeList()
        choices = list(filter_obj.choices(changelist))
        assert choices[0]["display"] == "All"

    def test_choices_yields_sorted_implementations(self, test_strategy_registry, admin_rf):
        filter_obj = _make_mock_filter(test_strategy_registry, admin_rf)
        changelist = MockChangeList()
        choices = list(filter_obj.choices(changelist))
        # First is "All", rest are implementations
        impl_choices = choices[1:]
        assert len(impl_choices) == 3

    def test_choices_no_registry_returns_nothing(self, admin_rf):
        filter_obj = _make_mock_filter(None, admin_rf)
        filter_obj.field.registry = None
        changelist = MockChangeList()
        result = list(filter_obj.choices(changelist))
        assert len(result) == 0

    def test_choices_selected_state(self, test_strategy_registry, admin_rf):
        filter_obj = _make_mock_filter(test_strategy_registry, admin_rf)
        filter_obj.lookup_val = "email"
        changelist = MockChangeList()
        choices = list(filter_obj.choices(changelist))
        # "All" should not be selected
        assert choices[0]["selected"] is False
        # Find the email choice and check it's selected
        email_choices = [c for c in choices[1:] if "email" in c.get("query_string", "")]
        assert len(email_choices) == 1
        assert email_choices[0]["selected"] is True

    def test_choices_all_selected_when_no_lookup(self, test_strategy_registry, admin_rf):
        filter_obj = _make_mock_filter(test_strategy_registry, admin_rf)
        changelist = MockChangeList()
        choices = list(filter_obj.choices(changelist))
        assert choices[0]["selected"] is True

    def test_choices_context_aware_filtering(self, conditional_registry, admin_rf):
        filter_obj = _make_mock_filter(conditional_registry, admin_rf)
        changelist = MockChangeList()
        choices = list(filter_obj.choices(changelist))
        impl_choices = choices[1:]
        slugs = [c.get("query_string", "") for c in impl_choices]
        assert any("basic_feature" in s for s in slugs)

    def test_choices_query_string_format(self, test_strategy_registry, admin_rf):
        filter_obj = _make_mock_filter(test_strategy_registry, admin_rf)
        changelist = MockChangeList()
        choices = list(filter_obj.choices(changelist))
        # All non-"All" choices should have query strings with the lookup kwarg
        for c in choices[1:]:
            assert "test_field__exact" in c["query_string"]

    def test_choices_display_names(self, test_strategy_registry, admin_rf):
        filter_obj = _make_mock_filter(test_strategy_registry, admin_rf)
        changelist = MockChangeList()
        choices = list(filter_obj.choices(changelist))
        displays = [c["display"] for c in choices[1:]]
        assert "Email Strategy" in displays
        assert "SMS Strategy" in displays
        assert "Push Strategy" in displays

    def test_init_stores_request(self, test_strategy_registry, admin_rf):
        """Test real instantiation of filter stores request attribute."""
        from tests.testapp.models import RegistryFieldTestModel

        db_field = RegistryFieldTestModel._meta.get_field("single_class")

        filter_obj = RegistryFieldListFilter(
            db_field,
            admin_rf,
            {},
            RegistryFieldTestModel,
            None,
            "single_class",
        )

        assert filter_obj.request is admin_rf


class TestContextAwareRegistryAdmin:
    """Tests for ContextAwareRegistryAdmin."""

    def test_get_form_returns_wrapped_form(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = ContextAwareRegistryAdmin(RegistryFieldTestModel, admin_site)
        form_class = admin_obj.get_form(admin_rf)
        assert form_class is not None

    def test_get_form_injects_context(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = ContextAwareRegistryAdmin(RegistryFieldTestModel, admin_site)
        form_class = admin_obj.get_form(admin_rf)
        form = form_class()
        assert form is not None

    def test_formfield_for_dbfield_registry_field(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = ContextAwareRegistryAdmin(RegistryFieldTestModel, admin_site)
        db_field = RegistryFieldTestModel._meta.get_field("single_class")
        # Exercises the isinstance(db_field, AbstractRegistryField) branch
        form_field = admin_obj.formfield_for_dbfield(db_field, admin_rf)
        assert form_field is not None

    def test_formfield_for_non_registry_field_unchanged(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = ContextAwareRegistryAdmin(RegistryFieldTestModel, admin_site)
        db_field = RegistryFieldTestModel._meta.get_field("name")
        form_field = admin_obj.formfield_for_dbfield(db_field, admin_rf)
        assert not isinstance(form_field, ContextAwareRegistryFormField)

    def test_get_form_creates_context_with_request(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = ContextAwareRegistryAdmin(RegistryFieldTestModel, admin_site)
        form_class = admin_obj.get_form(admin_rf, change=True)
        assert form_class is not None

    def test_formfield_for_dbfield_instance_field(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = ContextAwareRegistryAdmin(RegistryFieldTestModel, admin_site)
        db_field = RegistryFieldTestModel._meta.get_field("single_instance")
        form_field = admin_obj.formfield_for_dbfield(db_field, admin_rf)
        assert form_field is not None


class TestRegistryListMixin:
    """Tests for RegistryListMixin."""

    def test_get_list_display_appends_fields(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = RegistryListMixin(RegistryFieldTestModel, admin_site)
        list_display = admin_obj.get_list_display(admin_rf)
        assert len(list_display) > 1

    def test_get_list_filter_adds_registry_fields(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = RegistryListMixin(RegistryFieldTestModel, admin_site)
        list_filter = admin_obj.get_list_filter(admin_rf)
        registry_fields = [f.name for f in RegistryFieldTestModel._meta.fields if isinstance(f, AbstractRegistryField)]
        for rf_name in registry_fields:
            assert rf_name in list_filter

    def test_get_list_display_includes_model_field_names(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = RegistryListMixin(RegistryFieldTestModel, admin_site)
        list_display = admin_obj.get_list_display(admin_rf)
        assert "name" in list_display

    def test_get_list_filter_only_registry_fields(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = RegistryListMixin(RegistryFieldTestModel, admin_site)
        list_filter = admin_obj.get_list_filter(admin_rf)
        # "name" is a CharField, not a registry field, so it should not be in list_filter
        # (unless base returns it - we check our additions are registry fields)
        registry_field_names = {
            f.name for f in RegistryFieldTestModel._meta.fields if isinstance(f, AbstractRegistryField)
        }
        # All registry fields should be present
        assert registry_field_names.issubset(set(list_filter))


class TestHierarchicalRegistryAdmin:
    """Tests for HierarchicalRegistryAdmin."""

    def test_get_form_returns_hierarchical_form(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)
        form_class = admin_obj.get_form(admin_rf)
        assert form_class is not None

    def test_get_form_sets_up_hierarchical_fields(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)
        form_class = admin_obj.get_form(admin_rf)
        form = form_class()
        assert form is not None

    def test_media_includes_js(self, test_strategy_registry, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)
        assert "admin/js/hierarchical_registry.js" in admin_obj.media._js

    def test_get_form_with_change_flag(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)
        form_class = admin_obj.get_form(admin_rf, change=True)
        assert form_class is not None

    def test_formfield_for_choice_field_non_hierarchical(self, test_strategy_registry, admin_rf, admin_site):
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)
        # For non-hierarchical fields, should call super
        db_field = RegistryFieldTestModel._meta.get_field("name")
        admin_obj.formfield_for_choice_field(db_field, admin_rf)
        # Should just return whatever super returns without error

    def test_get_form_sets_widget_data_attrs(self, parent_registry, child_registry, admin_rf, admin_site):
        """Test hierarchical form field gets data-* widget attributes."""
        from django_stratagem.forms import HierarchicalRegistryFormField
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)
        form_class = admin_obj.get_form(admin_rf)
        form = form_class()

        # Inject a hierarchical form field
        hier_field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
            parent_field="name",
        )
        form.fields["test_hier"] = hier_field

        # Re-run setup to trigger the hierarchical field configuration
        form._setup_hierarchical_fields()

        assert hier_field.widget.attrs.get("data-hierarchical") == "true"
        assert hier_field.widget.attrs.get("data-registry") == "ChildTestRegistry"
        assert hier_field.widget.attrs.get("data-parent-field") == "name"

    def test_get_form_sets_parent_value_on_edit(self, parent_registry, child_registry, admin_rf, admin_site):
        """Test editing instance with parent value calls set_parent_value."""
        from django_stratagem.forms import HierarchicalRegistryFormField
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)
        instance = RegistryFieldTestModel(name="test_parent")

        form_class = admin_obj.get_form(admin_rf, obj=instance)
        form = form_class(instance=instance)

        # Inject a hierarchical form field with parent_field pointing to "name"
        hier_field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
            parent_field="name",
        )
        form.fields["test_hier"] = hier_field

        # Re-run setup - should detect instance.name and call set_parent_value
        form._setup_hierarchical_fields()

        assert hier_field.parent_value == "test_parent"

    def test_formfield_for_choice_field_hierarchical(self, parent_registry, child_registry, admin_rf, admin_site):
        """Test formfield_for_choice_field with HierarchicalRegistryField sets context."""
        from django_stratagem.fields import HierarchicalRegistryField
        from tests.testapp.models import RegistryFieldTestModel

        admin_obj = HierarchicalRegistryAdmin(RegistryFieldTestModel, admin_site)

        db_field = HierarchicalRegistryField(
            registry=child_registry,
            parent_field="name",
            verbose_name="Test Hier",
            blank=True,
        )
        db_field.name = "test_hier"

        result = admin_obj.formfield_for_choice_field(db_field, admin_rf)
        assert result is not None


class TestDjangoStratagemAdminSite:
    """Tests for DjangoStratagemAdminSite."""

    def test_get_urls_includes_dashboard(self):
        site = DjangoStratagemAdminSite()
        urls = site.get_urls()
        url_names = [url.name for url in urls if hasattr(url, "name")]
        assert "registry-dashboard" in url_names

    def test_registry_dashboard_returns_template_response(self, test_strategy_registry, admin_rf):
        site = DjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        assert response.status_code == 200
        assert "rows" in response.context_data
        assert "title" in response.context_data

    def test_registry_dashboard_context_contains_rows(self, test_strategy_registry, admin_rf):
        site = DjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        assert isinstance(rows, list)
        registry_names = [r["registry"] for r in rows]
        assert "TestStrategyRegistry" in registry_names

    def test_registry_dashboard_rows_have_implementations(self, test_strategy_registry, admin_rf):
        site = DjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        test_row = next(r for r in rows if r["registry"] == "TestStrategyRegistry")
        impls = test_row["implementations"]
        assert len(impls) == 3
        slugs = [i["slug"] for i in impls]
        assert "email" in slugs

    def test_registry_dashboard_shows_availability(self, conditional_registry, admin_rf):
        site = DjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        cond_row = next((r for r in rows if r["registry"] == "ConditionalTestRegistry"), None)
        assert cond_row is not None
        impls = cond_row["implementations"]
        premium = next((i for i in impls if i["slug"] == "premium_feature"), None)
        assert premium is not None
        assert premium["is_available"] is False

    def test_registry_dashboard_shows_description(self, test_strategy_registry, admin_rf):
        site = DjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        test_row = next(r for r in rows if r["registry"] == "TestStrategyRegistry")
        email_impl = next(i for i in test_row["implementations"] if i["slug"] == "email")
        assert email_impl["description"] == "Send notifications via email"

    def test_registry_dashboard_shows_icon(self, test_strategy_registry, admin_rf):
        site = DjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        test_row = next(r for r in rows if r["registry"] == "TestStrategyRegistry")
        email_impl = next(i for i in test_row["implementations"] if i["slug"] == "email")
        assert "fa-envelope" in email_impl["icon"]

    def test_registry_dashboard_title(self, test_strategy_registry, admin_rf):
        site = DjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        assert response.context_data["title"] == "Registry Dashboard"


class TestEnhancedDjangoStratagemAdminSite:
    """Tests for EnhancedDjangoStratagemAdminSite."""

    def test_get_urls_includes_enhanced_dashboard(self):
        site = EnhancedDjangoStratagemAdminSite()
        urls = site.get_urls()
        url_names = [url.name for url in urls if hasattr(url, "name")]
        assert "enhanced-registry-dashboard" in url_names

    def test_registry_dashboard_returns_response(self, test_strategy_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        assert response.status_code == 200
        assert "rows" in response.context_data

    def test_registry_dashboard_shows_hierarchy(self, parent_registry, child_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        parent_row = next((r for r in rows if r["registry"] == "ParentTestRegistry"), None)
        assert parent_row is not None
        assert len(parent_row["children"]) > 0

    def test_registry_dashboard_children_nested(self, parent_registry, child_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        parent_row = next(r for r in rows if r["registry"] == "ParentTestRegistry")
        child_info = parent_row["children"][0]
        assert child_info["registry"] == "ChildTestRegistry"
        assert len(child_info["implementations"]) > 0

    def test_unprocessed_registries_included(self, test_strategy_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        rows = response.context_data["rows"]
        registry_names = [r["registry"] for r in rows]
        assert "TestStrategyRegistry" in registry_names

    def test_get_registry_info_basic(self, test_strategy_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        context = {"request": admin_rf, "user": admin_rf.user}
        info = site._get_registry_info(test_strategy_registry, context)
        assert info["registry"] == "TestStrategyRegistry"
        assert len(info["implementations"]) == 3

    def test_get_registry_info_hierarchical(self, parent_registry, child_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        context = {"request": admin_rf, "user": admin_rf.user}
        info = site._get_registry_info(child_registry, context)
        assert info["parent_registry"] == "ParentTestRegistry"

    def test_get_registry_info_parent_requirements(self, parent_registry, child_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        context = {"request": admin_rf, "user": admin_rf.user}
        info = site._get_registry_info(child_registry, context)
        impls = info["implementations"]
        child_a = next(i for i in impls if i["slug"] == "child_of_a")
        assert child_a["parent_requirements"] == ["category_a"]

    def test_get_registry_info_multiple_parent_requirements(self, parent_registry, child_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        context = {"request": admin_rf, "user": admin_rf.user}
        info = site._get_registry_info(child_registry, context)
        impls = info["implementations"]
        child_both = next(i for i in impls if i["slug"] == "child_of_both")
        assert set(child_both["parent_requirements"]) == {"category_a", "category_b"}

    def test_relationships_in_context(self, parent_registry, child_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        response = site.registry_dashboard(admin_rf)
        assert "relationships" in response.context_data

    def test_get_registry_info_description(self, test_strategy_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        context = {"request": admin_rf, "user": admin_rf.user}
        info = site._get_registry_info(test_strategy_registry, context)
        assert "description" in info

    def test_get_registry_info_is_hierarchical_flag(self, test_strategy_registry, admin_rf):
        site = EnhancedDjangoStratagemAdminSite()
        context = {"request": admin_rf, "user": admin_rf.user}
        info = site._get_registry_info(test_strategy_registry, context)
        assert "is_hierarchical" in info
