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
