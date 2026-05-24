import pytest

from django_stratagem.conditions import CallableCondition
from django_stratagem.interfaces import ConditionalInterface


def test_explain_availability_no_condition_is_available():
    class AlwaysOn(ConditionalInterface):
        pass

    available, reason = AlwaysOn.explain_availability({})
    assert available is True
    assert "no condition" in reason.lower()


def test_explain_availability_reports_condition_failure():
    class NeedsOk(ConditionalInterface):
        condition = CallableCondition(lambda ctx: ctx.get("ok", False))

    available, reason = NeedsOk.explain_availability({"ok": False})
    assert available is False
    assert "failed" in reason.lower()


def test_explain_availability_reports_condition_success():
    class NeedsOk(ConditionalInterface):
        condition = CallableCondition(lambda ctx: ctx.get("ok", False))

    available, reason = NeedsOk.explain_availability({"ok": True})
    assert available is True
    assert "passed" in reason.lower()


def test_explain_availability_handles_none_context():
    class AlwaysOn(ConditionalInterface):
        pass

    available, reason = AlwaysOn.explain_availability()
    assert available is True


def test_build_inspector_rows_lists_registered_implementations(test_strategy_registry):
    from django_stratagem.inspector import build_inspector_rows

    rows = build_inspector_rows({})
    by_name = {row["registry"]: row for row in rows}
    assert "TestStrategyRegistry" in by_name

    row = by_name["TestStrategyRegistry"]
    slugs = {impl["slug"] for impl in row["implementations"]}
    assert {"email", "sms", "push"} <= slugs
    assert all(impl["available"] for impl in row["implementations"])
    assert all("reason" in impl for impl in row["implementations"])


def test_build_inspector_rows_sorted_by_priority(test_strategy_registry):
    from django_stratagem.inspector import build_inspector_rows

    row = next(r for r in build_inspector_rows({}) if r["registry"] == "TestStrategyRegistry")
    priorities = [impl["priority"] for impl in row["implementations"]]
    assert priorities == sorted(priorities)


def test_build_inspector_rows_defaults_context_to_empty():
    from django_stratagem.inspector import build_inspector_rows

    rows = build_inspector_rows()
    assert isinstance(rows, list)


def test_build_inspector_rows_isolates_failing_explain(test_strategy_registry, caplog):
    import logging

    from django_stratagem.inspector import build_inspector_rows
    from tests.registries_fixtures import TestStrategyRegistry

    def boom(context):
        raise RuntimeError("kaboom")

    # Attach a raising explain_availability to one registered implementation class.
    email_class = TestStrategyRegistry.implementations["email"]["klass"]
    original = email_class.__dict__.get("explain_availability", None)
    email_class.explain_availability = classmethod(lambda cls, context=None: boom(context))
    try:
        with caplog.at_level(logging.ERROR, logger="django_stratagem.inspector"):
            rows = build_inspector_rows({})
    finally:
        if original is None:
            del email_class.explain_availability
        else:
            email_class.explain_availability = original

    row = next(r for r in rows if r["registry"] == "TestStrategyRegistry")
    by_slug = {impl["slug"]: impl for impl in row["implementations"]}
    # The failing implementation degrades to a single unavailable row.
    assert by_slug["email"]["available"] is False
    # The raw exception text is logged, not leaked into the rendered response.
    assert "kaboom" not in by_slug["email"]["reason"]
    assert "see server logs" in by_slug["email"]["reason"]
    assert any(record.exc_info for record in caplog.records)
    # Other implementations are unaffected.
    assert by_slug["sms"]["available"] is True


def test_inspector_url_is_registered():
    from django_stratagem.urls import urlpatterns

    names = [getattr(pattern, "name", None) for pattern in urlpatterns]
    assert "registry-inspector" in names


@pytest.mark.django_db
def test_inspector_view_renders_for_staff(rf, django_user_model, test_strategy_registry):
    from django_stratagem.inspector import registry_inspector

    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    request = rf.get("/inspector/")
    request.user = user

    response = registry_inspector(request)
    response.render()
    assert response.status_code == 200
    assert b"Registry Inspector" in response.content
    assert b"TestStrategyRegistry" in response.content


@pytest.mark.django_db
def test_inspector_view_redirects_anonymous(rf, django_user_model):
    from django.contrib.auth.models import AnonymousUser

    from django_stratagem.inspector import registry_inspector

    request = rf.get("/inspector/")
    request.user = AnonymousUser()

    response = registry_inspector(request)
    assert response.status_code == 302


def test_inspector_url_name_constant():
    from django_stratagem.inspector import INSPECTOR_URL_NAME

    assert INSPECTOR_URL_NAME == "django_stratagem:registry-inspector"


@pytest.mark.django_db
def test_inspector_view_rejects_non_staff_authenticated_user(rf, django_user_model):
    from django_stratagem.inspector import registry_inspector

    user = django_user_model.objects.create_user("regular", password="pw", is_staff=False)
    request = rf.get("/inspector/")
    request.user = user

    response = registry_inspector(request)
    assert response.status_code == 302


def test_build_inspector_rows_reports_is_available_override(conditional_registry):
    from django_stratagem.inspector import build_inspector_rows

    # PremiumFeature overrides is_available directly (no condition / no
    # explain_availability); with an empty context it is unavailable. The
    # inspector must reflect that rather than defaulting to "always available".
    rows = build_inspector_rows({})
    row = next(r for r in rows if r["registry"] == "ConditionalTestRegistry")
    by_slug = {impl["slug"]: impl for impl in row["implementations"]}
    assert by_slug["premium_feature"]["available"] is False
    assert by_slug["basic_feature"]["available"] is True


def test_build_inspector_rows_isolates_failing_display_name(test_strategy_registry, monkeypatch, caplog):
    import logging

    from django_stratagem.inspector import build_inspector_rows
    from tests.registries_fixtures import TestStrategyRegistry

    def boom(cls, implementation):
        raise RuntimeError("name kaboom")

    monkeypatch.setattr(TestStrategyRegistry, "get_display_name", classmethod(boom))

    with caplog.at_level(logging.ERROR, logger="django_stratagem.inspector"):
        rows = build_inspector_rows({})

    row = next(r for r in rows if r["registry"] == "TestStrategyRegistry")
    by_slug = {impl["slug"]: impl for impl in row["implementations"]}
    # A display-name failure degrades to the slug and is logged, without
    # affecting the availability column.
    assert by_slug["email"]["name"] == "email"
    assert by_slug["email"]["available"] is True
    assert "kaboom" not in by_slug["email"]["name"]
    assert any(record.exc_info for record in caplog.records)
