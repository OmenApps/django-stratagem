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
