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
