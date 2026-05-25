def test_temporary_implementation_registers_then_restores(test_strategy_registry):
    from django_stratagem.interfaces import Interface
    from django_stratagem.testing import temporary_implementation

    class TempStrategy(Interface):
        slug = "temp"
        display_name = "Temp Strategy"

    assert "temp" not in test_strategy_registry.implementations

    with temporary_implementation(test_strategy_registry, TempStrategy) as impl:
        assert impl is TempStrategy
        assert "temp" in test_strategy_registry.implementations
        assert test_strategy_registry.get_class(slug="temp") is TempStrategy

    assert "temp" not in test_strategy_registry.implementations


def test_temporary_implementation_restores_on_exception(test_strategy_registry):
    from django_stratagem.interfaces import Interface
    from django_stratagem.testing import temporary_implementation

    class TempStrategy(Interface):
        slug = "temp"
        display_name = "Temp Strategy"

    try:
        with temporary_implementation(test_strategy_registry, TempStrategy):
            assert "temp" in test_strategy_registry.implementations
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert "temp" not in test_strategy_registry.implementations


def test_override_availability_forces_unavailable():
    from django_stratagem.interfaces import ConditionalInterface
    from django_stratagem.testing import override_availability

    class Feature(ConditionalInterface):
        slug = "feat"

    # No condition means available by default.
    assert Feature.is_available({}) is True

    with override_availability(Feature, available=False):
        assert Feature.is_available({}) is False

    assert Feature.is_available({}) is True


def test_override_availability_forces_available_for_impl_with_own_method():
    from django_stratagem.interfaces import ConditionalInterface
    from django_stratagem.testing import override_availability

    class Gated(ConditionalInterface):
        slug = "gated"

        @classmethod
        def is_available(cls, context=None):
            return False

    assert Gated.is_available({}) is False

    with override_availability(Gated, available=True):
        assert Gated.is_available({}) is True

    # Original (own) method is restored.
    assert Gated.is_available({}) is False


def test_isolate_registries_restores_global_list_and_implementations(test_strategy_registry):
    from django_stratagem.registry import Registry, django_stratagem_registry
    from django_stratagem.testing import isolate_registries

    before_list = list(django_stratagem_registry)
    before_impls = dict(test_strategy_registry.implementations)

    with isolate_registries():

        class Ephemeral(Registry):
            implementations_module = "ephemeral_impls"

        assert Ephemeral in django_stratagem_registry
        test_strategy_registry.implementations.clear()
        assert test_strategy_registry.implementations == {}

    assert list(django_stratagem_registry) == before_list
    assert test_strategy_registry.implementations == before_impls


def test_assert_registered_passes_and_fails(test_strategy_registry):
    from django_stratagem.testing import assert_not_registered, assert_registered

    assert_registered(test_strategy_registry, "email")
    assert_not_registered(test_strategy_registry, "nope")

    import pytest

    with pytest.raises(AssertionError) as excinfo:
        assert_registered(test_strategy_registry, "nope")
    assert "nope" in str(excinfo.value)
    assert "email" in str(excinfo.value)

    with pytest.raises(AssertionError):
        assert_not_registered(test_strategy_registry, "email")


def test_assert_available_and_not_available():
    from django_stratagem.interfaces import ConditionalInterface
    from django_stratagem.testing import assert_available, assert_not_available

    class Gated(ConditionalInterface):
        slug = "gated"

        @classmethod
        def is_available(cls, context=None):
            return bool(context and context.get("ok"))

    assert_available(Gated, {"ok": True})
    assert_not_available(Gated, {"ok": False})

    import pytest

    with pytest.raises(AssertionError):
        assert_available(Gated, {"ok": False})
    with pytest.raises(AssertionError):
        assert_not_available(Gated, {"ok": True})


def test_assert_choices_matches_registered_slugs(test_strategy_registry):
    from django_stratagem.testing import assert_choices

    # Priority order: email (10), sms (20), push (30).
    assert_choices(test_strategy_registry, ["email", "sms", "push"])

    import pytest

    with pytest.raises(AssertionError) as excinfo:
        assert_choices(test_strategy_registry, ["email"])
    assert "email" in str(excinfo.value)
