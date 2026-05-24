from asgiref.sync import async_to_sync


def test_callable_condition_acheck():
    from django_stratagem.conditions import CallableCondition

    cond = CallableCondition(lambda ctx: ctx.get("ok", False))
    assert async_to_sync(cond.acheck)({"ok": True}) is True
    assert async_to_sync(cond.acheck)({"ok": False}) is False


def test_all_conditions_acheck():
    from django_stratagem.conditions import CallableCondition

    truthy = CallableCondition(lambda ctx: True)
    falsy = CallableCondition(lambda ctx: False)
    assert async_to_sync((truthy & falsy).acheck)({}) is False
    assert async_to_sync((truthy & truthy).acheck)({}) is True


def test_any_conditions_acheck():
    from django_stratagem.conditions import CallableCondition

    truthy = CallableCondition(lambda ctx: True)
    falsy = CallableCondition(lambda ctx: False)
    assert async_to_sync((truthy | falsy).acheck)({}) is True
    assert async_to_sync((falsy | falsy).acheck)({}) is False


def test_not_condition_acheck():
    from django_stratagem.conditions import CallableCondition

    falsy = CallableCondition(lambda ctx: False)
    assert async_to_sync((~falsy).acheck)({}) is True


def test_ais_available_no_condition():
    from django_stratagem.interfaces import ConditionalInterface

    class AlwaysOn(ConditionalInterface):
        pass

    assert async_to_sync(AlwaysOn.ais_available)({}) is True


def test_ais_available_with_condition():
    from django_stratagem.conditions import CallableCondition
    from django_stratagem.interfaces import ConditionalInterface

    class Gated(ConditionalInterface):
        condition = CallableCondition(lambda ctx: ctx.get("ok", False))

    assert async_to_sync(Gated.ais_available)({"ok": True}) is True
    assert async_to_sync(Gated.ais_available)({"ok": False}) is False


def test_ais_available_defaults_context():
    from django_stratagem.interfaces import ConditionalInterface

    class AlwaysOn(ConditionalInterface):
        pass

    assert async_to_sync(AlwaysOn.ais_available)() is True


def test_aget_available_implementations(test_strategy_registry):
    from tests.registries_fixtures import TestStrategyRegistry

    result = async_to_sync(TestStrategyRegistry.aget_available_implementations)({})
    assert {"email", "sms", "push"} <= set(result)


def test_aget_available_filters_conditional(conditional_registry):
    # ConditionalTestRegistry has BasicFeature (always) and PremiumFeature
    # (only for premium users). With an empty context, premium is excluded.
    from tests.registries_fixtures import ConditionalTestRegistry

    result = async_to_sync(ConditionalTestRegistry.aget_available_implementations)({})
    assert "basic_feature" in result
    assert "premium_feature" not in result


def test_aget_choices_for_context_sorted(test_strategy_registry):
    from tests.registries_fixtures import TestStrategyRegistry

    choices = async_to_sync(TestStrategyRegistry.aget_choices_for_context)({})
    slugs = [slug for slug, _ in choices]
    # email(10) < sms(20) < push(30) by priority
    assert slugs == ["email", "sms", "push"]


def test_aget_returns_instance(test_strategy_registry):
    from tests.registries_fixtures import EmailStrategy, TestStrategyRegistry

    impl = async_to_sync(TestStrategyRegistry.aget)(slug="email")
    assert isinstance(impl, EmailStrategy)
