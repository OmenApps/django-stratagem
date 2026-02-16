"""Tests for django_stratagem DRF views module."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from django_stratagem.drf.views import (
    RegistryChoicesAPIView,
    RegistryHierarchyAPIView,
)
from django_stratagem.registry import django_stratagem_registry

pytestmark = pytest.mark.django_db


class TestRegistryChoicesAPIView:
    """Tests for RegistryChoicesAPIView."""

    @pytest.fixture
    def view(self):
        """Create view instance."""
        return RegistryChoicesAPIView()

    @pytest.fixture
    def rf(self):
        """Create request factory."""
        return RequestFactory()

    def test_get_without_registry_returns_400(self, rf, view):
        """Test GET without registry parameter returns 400."""
        request = rf.get("/api/registry-choices/")
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
        assert "Registry name required" in data["error"]

    def test_get_with_nonexistent_registry_returns_404(self, rf, view):
        """Test GET with nonexistent registry returns 404."""
        request = rf.get("/api/registry-choices/", {"registry": "NonExistentRegistry"})
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 404
        data = json.loads(response.content)
        assert "error" in data
        assert "Registry not found" in data["error"]

    def test_get_with_valid_registry(self, rf, view, test_strategy_registry):
        """Test GET with valid registry returns choices."""
        # Ensure registry is in global registry
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "TestStrategyRegistry"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "choices" in data
        assert "registry" in data
        assert data["registry"] == "TestStrategyRegistry"

    def test_get_with_authenticated_user(self, rf, view, test_strategy_registry, basic_user):
        """Test GET includes user in context when authenticated."""
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "TestStrategyRegistry"},
        )
        request.user = basic_user

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "choices" in data

    def test_get_with_anonymous_user(self, rf, view, test_strategy_registry):
        """Test GET handles anonymous user correctly."""
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "TestStrategyRegistry"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "choices" in data

    def test_get_with_parent_for_hierarchical_registry(self, rf, view, parent_registry, child_registry):
        """Test GET with parent parameter for hierarchical registry."""
        # Add registries to global registry
        if parent_registry not in django_stratagem_registry:
            django_stratagem_registry.append(parent_registry)
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "ChildTestRegistry", "parent": "category_a"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "choices" in data
        assert data["parent"] == "category_a"

    def test_get_with_invalid_parent_slug(self, rf, view, child_registry):
        """Test GET with invalid parent slug returns all choices.

        Note: When an invalid parent is provided, the view returns all choices
        rather than an empty list. This is because _get_parent_slug returns None
        for invalid slugs, and the view then fetches all choices without filtering.
        """
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "ChildTestRegistry", "parent": "invalid_parent"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        # Invalid parent returns all choices (not filtered)
        # This is current behavior - choices are not filtered when parent is invalid
        assert isinstance(data["choices"], list)

    def test_response_includes_registry_name(self, rf, view, test_strategy_registry):
        """Test response includes registry name."""
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "TestStrategyRegistry"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)

        assert data["registry"] == "TestStrategyRegistry"

    def test_response_includes_parent_value(self, rf, view, test_strategy_registry):
        """Test response includes parent value when provided."""
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "TestStrategyRegistry", "parent": "some_parent"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)

        assert data["parent"] == "some_parent"

    def test_get_with_valid_parent_fqn_returns_filtered_choices(
        self, rf, view, parent_registry, child_registry
    ):
        """Test GET with valid parent FQN returns filtered child choices."""
        from tests.registries_fixtures import CategoryA

        fqn = f"{CategoryA.__module__}.{CategoryA.__name__}"
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "ChildTestRegistry", "parent": fqn},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert data["parent"] == fqn

    def test_get_with_unresolvable_parent_returns_empty_choices(
        self, rf, view, parent_registry, child_registry
    ):
        """Test GET with unresolvable parent FQN returns empty choices."""
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        request = rf.get(
            "/api/registry-choices/",
            {"registry": "ChildTestRegistry", "parent": "invalid.module.FakeClass"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["choices"] == []


class TestRegistryChoicesAPIViewGetParentSlug:
    """Tests for _get_parent_slug method."""

    @pytest.fixture
    def view(self):
        """Create view instance."""
        return RegistryChoicesAPIView()

    def test_get_parent_slug_with_none(self, view, child_registry):
        """Test _get_parent_slug returns None for None input."""
        result = view._get_parent_slug(child_registry, None)
        assert result is None

    def test_get_parent_slug_with_empty_string(self, view, child_registry):
        """Test _get_parent_slug returns None for empty string."""
        result = view._get_parent_slug(child_registry, "")
        assert result is None

    def test_get_parent_slug_with_valid_slug(self, view, child_registry):
        """Test _get_parent_slug recognizes valid slug."""
        result = view._get_parent_slug(child_registry, "category_a")
        assert result == "category_a"

    def test_get_parent_slug_with_invalid_slug(self, view, child_registry):
        """Test _get_parent_slug returns None for invalid slug."""
        result = view._get_parent_slug(child_registry, "invalid_slug")
        assert result is None

    def test_get_parent_slug_with_fqn(self, view, parent_registry, child_registry):
        """Test _get_parent_slug resolves FQN to parent slug."""
        from tests.registries_fixtures import CategoryA

        fqn = f"{CategoryA.__module__}.{CategoryA.__name__}"
        result = view._get_parent_slug(child_registry, fqn)
        assert result == "category_a"

    def test_get_parent_slug_no_parent_registry(self, view):
        """Test _get_parent_slug returns None when parent_registry is None."""
        from unittest.mock import MagicMock

        mock_registry = MagicMock()
        mock_registry.parent_registry = None
        result = view._get_parent_slug(mock_registry, "some_value")
        assert result is None

    def test_get_parent_slug_fqn_import_fails(self, view, parent_registry, child_registry):
        """Test _get_parent_slug returns None when FQN import fails."""
        result = view._get_parent_slug(child_registry, "nonexistent.module.FakeClass")
        assert result is None


class TestRegistryHierarchyAPIView:
    """Tests for RegistryHierarchyAPIView."""

    @pytest.fixture
    def view(self):
        """Create view instance."""
        return RegistryHierarchyAPIView()

    @pytest.fixture
    def rf(self):
        """Create request factory."""
        return RequestFactory()

    def test_get_returns_hierarchies(self, rf, view):
        """Test GET returns hierarchy data."""
        request = rf.get("/api/registry-hierarchy/")
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "hierarchies" in data

    def test_get_includes_hierarchical_registries(self, rf, view, parent_registry, child_registry):
        """Test GET includes hierarchical registry data."""
        # Add registries to global registry
        if parent_registry not in django_stratagem_registry:
            django_stratagem_registry.append(parent_registry)
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        request = rf.get("/api/registry-hierarchy/")
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "hierarchies" in data
        # ChildTestRegistry should be included as hierarchical

    def test_hierarchical_data_includes_parent_registry_name(self, rf, view, child_registry):
        """Test hierarchy data includes parent registry name."""
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        request = rf.get("/api/registry-hierarchy/")
        request.user = AnonymousUser()

        response = view.get(request)
        data = json.loads(response.content)

        # If ChildTestRegistry is included, verify parent_registry field
        if "ChildTestRegistry" in data["hierarchies"]:
            child_data = data["hierarchies"]["ChildTestRegistry"]
            assert "parent_registry" in child_data

    def test_response_is_json(self, rf, view):
        """Test response is valid JSON."""
        request = rf.get("/api/registry-hierarchy/")
        request.user = AnonymousUser()

        response = view.get(request)

        assert response["Content-Type"] == "application/json"
        # Should not raise
        json.loads(response.content)

    def test_empty_hierarchy_map_excluded(self, rf, view):
        """Test hierarchical registry with empty hierarchy map is excluded."""
        from django_stratagem.registry import HierarchicalRegistry

        # This class is auto-added to django_stratagem_registry via __init_subclass__
        class EmptyHierarchicalRegistry(HierarchicalRegistry):
            implementations_module = "empty_test_implementations"
            parent_registry = None  # No parent → get_hierarchy_map returns {}

        request = rf.get("/api/registry-hierarchy/")
        request.user = AnonymousUser()

        response = view.get(request)
        data = json.loads(response.content)

        assert "EmptyHierarchicalRegistry" not in data["hierarchies"]

    def test_hierarchy_data_structure_complete(
        self, rf, view, parent_registry, child_registry
    ):
        """Test hierarchy data includes parent_registry and hierarchy_map keys."""
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        request = rf.get("/api/registry-hierarchy/")
        request.user = AnonymousUser()

        response = view.get(request)
        data = json.loads(response.content)

        assert "ChildTestRegistry" in data["hierarchies"]
        child_data = data["hierarchies"]["ChildTestRegistry"]
        assert "parent_registry" in child_data
        assert "hierarchy_map" in child_data
        assert child_data["parent_registry"] == "ParentTestRegistry"
        assert isinstance(child_data["hierarchy_map"], dict)


class TestDRFViewsEdgeCases:
    """Tests for edge cases in DRF views."""

    @pytest.fixture
    def rf(self):
        """Create request factory."""
        return RequestFactory()

    def test_choices_view_handles_empty_get_params(self, rf):
        """Test choices view handles empty GET parameters."""
        view = RegistryChoicesAPIView()
        request = rf.get("/api/registry-choices/", {})
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 400

    @pytest.mark.parametrize(
        "registry_name",
        [
            "",
            " ",
            "Registry With Spaces",
            "registry<script>",
        ],
    )
    def test_choices_view_handles_special_registry_names(self, rf, registry_name):
        """Test choices view handles special characters in registry name."""
        view = RegistryChoicesAPIView()
        request = rf.get("/api/registry-choices/", {"registry": registry_name})
        request.user = AnonymousUser()

        response = view.get(request)

        # Should either return 400 (empty) or 404 (not found)
        assert response.status_code in [400, 404]

    def test_hierarchy_view_with_no_hierarchical_registries(self, rf):
        """Test hierarchy view handles case with no hierarchical registries."""
        view = RegistryHierarchyAPIView()
        request = rf.get("/api/registry-hierarchy/")
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        # Should return empty hierarchies dict if none exist
        assert "hierarchies" in data
        assert isinstance(data["hierarchies"], dict)

    def test_choices_view_parent_with_dots_in_value(self, rf, child_registry):
        """Test choices view handles parent value with dots (FQN).

        Note: When an invalid parent value (including FQN-like strings) is provided,
        the view returns all choices rather than filtering. This is because
        _get_parent_slug returns None for invalid/unrecognized parent values.
        """
        if child_registry not in django_stratagem_registry:
            django_stratagem_registry.append(child_registry)

        view = RegistryChoicesAPIView()
        # Parent value that looks like FQN but is invalid
        request = rf.get(
            "/api/registry-choices/",
            {"registry": "ChildTestRegistry", "parent": "some.module.Class"},
        )
        request.user = AnonymousUser()

        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        # Invalid FQN returns all choices (not filtered) - current behavior
        assert isinstance(data["choices"], list)
