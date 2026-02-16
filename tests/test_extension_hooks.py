"""Tests for Registry extension hook methods."""

from __future__ import annotations

import pytest

from django_stratagem.exceptions import ImplementationNotFound
from django_stratagem.interfaces import Interface
from django_stratagem.registry import HierarchicalRegistry, Registry, register
from django_stratagem.signals import implementation_registered, implementation_unregistered


class HookTestRegistry(Registry):
    implementations_module = "hook_test_implementations"


class HookTestInterface(Interface):
    registry = None  # Don't auto-register


class AlphaImpl(HookTestInterface):
    slug = "alpha"
    description = "Alpha implementation"
    icon = "fa-alpha"
    priority = 10


class BetaImpl(HookTestInterface):
    slug = "beta"
    description = "Beta implementation"
    icon = "fa-beta"
    priority = 20


@pytest.fixture(autouse=True)
def _clean_hook_registry():
    """Reset HookTestRegistry implementations between tests."""
    HookTestRegistry.implementations = {}
    yield
    HookTestRegistry.implementations = {}
    HookTestRegistry.clear_cache()


class TestValidateImplementation:
    """Tests for the validate_implementation hook."""

    def test_default_rejects_no_slug(self):
        class NoSlug(HookTestInterface):
            pass

        with pytest.raises(ValueError, match="non-empty 'slug'"):
            HookTestRegistry.register(NoSlug)

    def test_default_rejects_empty_slug(self):
        class EmptySlug(HookTestInterface):
            slug = ""

        with pytest.raises(ValueError, match="non-empty 'slug'"):
            HookTestRegistry.register(EmptySlug)

    def test_default_rejects_wrong_interface(self):
        class StrictRegistry(Registry):
            implementations_module = "strict_impls"
            interface_class = HookTestInterface

        StrictRegistry.implementations = {}

        class Unrelated:
            slug = "unrelated"

        with pytest.raises(TypeError, match="must inherit from"):
            StrictRegistry.register(Unrelated)

    def test_default_accepts_valid_implementation(self):
        HookTestRegistry.register(AlphaImpl)
        assert "alpha" in HookTestRegistry.implementations

    def test_custom_validation_can_reject(self):
        class ValidatingRegistry(Registry):
            implementations_module = "validating_impls"

            @classmethod
            def validate_implementation(cls, implementation):
                super().validate_implementation(implementation)
                if not hasattr(implementation, "execute"):
                    raise ValueError("Implementation must define an execute() method")

        ValidatingRegistry.implementations = {}

        # AlphaImpl lacks execute()
        with pytest.raises(ValueError, match="execute"):
            ValidatingRegistry.register(AlphaImpl)

        assert not ValidatingRegistry.implementations

    def test_custom_validation_accepts_when_satisfied(self):
        class ValidatingRegistry(Registry):
            implementations_module = "validating_impls"

            @classmethod
            def validate_implementation(cls, implementation):
                super().validate_implementation(implementation)
                if not hasattr(implementation, "execute"):
                    raise ValueError("Implementation must define an execute() method")

        ValidatingRegistry.implementations = {}

        class WithExecute(HookTestInterface):
            slug = "with_execute"

            def execute(self):
                pass

        ValidatingRegistry.register(WithExecute)
        assert "with_execute" in ValidatingRegistry.implementations

    def test_super_chain_works(self):
        """Calling super() in validate_implementation preserves slug/interface checks."""

        class ChainedRegistry(Registry):
            implementations_module = "chained_impls"
            interface_class = HookTestInterface

            @classmethod
            def validate_implementation(cls, implementation):
                super().validate_implementation(implementation)
                if getattr(implementation, "priority", 0) < 0:
                    raise ValueError("Priority must be non-negative")

        ChainedRegistry.implementations = {}

        # Fails parent check (wrong interface)
        class BadInterface:
            slug = "bad"

        with pytest.raises(TypeError):
            ChainedRegistry.register(BadInterface)

        # Fails custom check
        class NegPriority(HookTestInterface):
            slug = "neg"
            priority = -1

        with pytest.raises(ValueError, match="non-negative"):
            ChainedRegistry.register(NegPriority)

    def test_failure_prevents_registration(self):
        class RejectAllRegistry(Registry):
            implementations_module = "reject_all"

            @classmethod
            def validate_implementation(cls, implementation):
                raise ValueError("Rejected")

        RejectAllRegistry.implementations = {}

        with pytest.raises(ValueError, match="Rejected"):
            RejectAllRegistry.register(AlphaImpl)

        assert not RejectAllRegistry.implementations


class TestBuildImplementationMeta:
    """Tests for the build_implementation_meta hook."""

    def test_default_keys_and_values(self):
        meta = HookTestRegistry.build_implementation_meta(AlphaImpl)
        assert meta["klass"] is AlphaImpl
        assert meta["description"] == "Alpha implementation"
        assert meta["icon"] == "fa-alpha"
        assert meta["priority"] == 10

    def test_default_keys_for_minimal_impl(self):
        class Minimal(HookTestInterface):
            slug = "minimal"

        meta = HookTestRegistry.build_implementation_meta(Minimal)
        assert meta["klass"] is Minimal
        assert meta["description"] == ""
        assert meta["icon"] == ""
        assert meta["priority"] == 0

    def test_custom_meta_adds_extra_keys(self):
        class RichRegistry(Registry):
            implementations_module = "rich_impls"

            @classmethod
            def build_implementation_meta(cls, implementation):
                meta = super().build_implementation_meta(implementation)
                meta["version"] = getattr(implementation, "version", "0.0.0")
                meta["author"] = getattr(implementation, "author", "unknown")
                return meta

        RichRegistry.implementations = {}

        class Versioned(HookTestInterface):
            slug = "versioned"
            version = "1.2.3"
            author = "test_author"

        RichRegistry.register(Versioned)
        stored = RichRegistry.implementations["versioned"]
        assert stored["klass"] is Versioned
        assert stored["version"] == "1.2.3"
        assert stored["author"] == "test_author"

    def test_super_preserves_defaults(self):
        class ExtendedRegistry(Registry):
            implementations_module = "extended_impls"

            @classmethod
            def build_implementation_meta(cls, implementation):
                meta = super().build_implementation_meta(implementation)
                meta["custom_flag"] = True
                return meta

        ExtendedRegistry.implementations = {}
        ExtendedRegistry.register(AlphaImpl)
        stored = ExtendedRegistry.implementations["alpha"]
        # Default keys still present
        assert stored["klass"] is AlphaImpl
        assert stored["description"] == "Alpha implementation"
        assert stored["icon"] == "fa-alpha"
        assert stored["priority"] == 10
        # Custom key added
        assert stored["custom_flag"] is True

    def test_meta_stored_matches_build_output(self):
        HookTestRegistry.register(AlphaImpl)
        built = HookTestRegistry.build_implementation_meta(AlphaImpl)
        stored = HookTestRegistry.implementations["alpha"]
        assert built == stored


class TestOnRegister:
    """Tests for the on_register hook."""

    def test_called_during_register(self):
        class TrackingRegistry(Registry):
            implementations_module = "tracking_impls"
            register_calls: list = []

            @classmethod
            def on_register(cls, slug, implementation, meta):
                cls.register_calls.append((slug, implementation, meta))

        TrackingRegistry.implementations = {}
        TrackingRegistry.register_calls = []

        TrackingRegistry.register(AlphaImpl)

        assert len(TrackingRegistry.register_calls) == 1
        slug, impl, meta = TrackingRegistry.register_calls[0]
        assert slug == "alpha"
        assert impl is AlphaImpl
        assert meta["klass"] is AlphaImpl

    def test_called_after_storage(self):
        """on_register is called after the implementation is stored."""

        class CheckStorageRegistry(Registry):
            implementations_module = "check_storage"
            was_stored: bool = False

            @classmethod
            def on_register(cls, slug, implementation, meta):
                cls.was_stored = slug in cls.implementations

        CheckStorageRegistry.implementations = {}
        CheckStorageRegistry.register(AlphaImpl)
        assert CheckStorageRegistry.was_stored is True

    def test_called_before_signal(self):
        """on_register is called before the implementation_registered signal."""
        call_order = []

        class OrderRegistry(Registry):
            implementations_module = "order_impls"

            @classmethod
            def on_register(cls, slug, implementation, meta):
                call_order.append("hook")

        def signal_handler(sender, **kwargs):
            call_order.append("signal")

        OrderRegistry.implementations = {}
        implementation_registered.connect(signal_handler)
        try:
            OrderRegistry.register(AlphaImpl)
            assert call_order == ["hook", "signal"]
        finally:
            implementation_registered.disconnect(signal_handler)

    def test_default_is_noop(self):
        # Should not raise
        HookTestRegistry.register(AlphaImpl)
        assert "alpha" in HookTestRegistry.implementations


class TestOnUnregister:
    """Tests for the on_unregister hook."""

    def test_called_during_unregister(self):
        class TrackingRegistry(Registry):
            implementations_module = "tracking_impls"
            unregister_calls: list = []

            @classmethod
            def on_unregister(cls, slug, meta):
                cls.unregister_calls.append((slug, meta))

        TrackingRegistry.implementations = {}
        TrackingRegistry.unregister_calls = []

        TrackingRegistry.register(AlphaImpl)
        TrackingRegistry.unregister("alpha")

        assert len(TrackingRegistry.unregister_calls) == 1
        slug, meta = TrackingRegistry.unregister_calls[0]
        assert slug == "alpha"
        assert meta["klass"] is AlphaImpl

    def test_receives_correct_meta(self):
        class MetaRegistry(Registry):
            implementations_module = "meta_impls"
            captured_meta: dict = {}

            @classmethod
            def build_implementation_meta(cls, implementation):
                meta = super().build_implementation_meta(implementation)
                meta["extra"] = "data"
                return meta

            @classmethod
            def on_unregister(cls, slug, meta):
                cls.captured_meta = dict(meta)

        MetaRegistry.implementations = {}
        MetaRegistry.captured_meta = {}

        MetaRegistry.register(AlphaImpl)
        MetaRegistry.unregister("alpha")
        assert MetaRegistry.captured_meta["extra"] == "data"
        assert MetaRegistry.captured_meta["klass"] is AlphaImpl

    def test_called_after_removal(self):
        class CheckRemovalRegistry(Registry):
            implementations_module = "check_removal"
            was_removed: bool = False

            @classmethod
            def on_unregister(cls, slug, meta):
                cls.was_removed = slug not in cls.implementations

        CheckRemovalRegistry.implementations = {}
        CheckRemovalRegistry.register(AlphaImpl)
        CheckRemovalRegistry.unregister("alpha")
        assert CheckRemovalRegistry.was_removed is True

    def test_called_before_signal(self):
        call_order = []

        class OrderRegistry(Registry):
            implementations_module = "order_impls2"

            @classmethod
            def on_unregister(cls, slug, meta):
                call_order.append("hook")

        def signal_handler(sender, **kwargs):
            call_order.append("signal")

        OrderRegistry.implementations = {}
        implementation_unregistered.connect(signal_handler)
        try:
            OrderRegistry.register(AlphaImpl)
            OrderRegistry.unregister("alpha")
            assert call_order == ["hook", "signal"]
        finally:
            implementation_unregistered.disconnect(signal_handler)

    def test_not_called_for_missing_slug(self):
        class TrackingRegistry(Registry):
            implementations_module = "tracking_impls2"
            unregister_calls: list = []

            @classmethod
            def on_unregister(cls, slug, meta):
                cls.unregister_calls.append(slug)

        TrackingRegistry.implementations = {}
        TrackingRegistry.unregister_calls = []

        with pytest.raises(ImplementationNotFound):
            TrackingRegistry.unregister("nonexistent")

        assert not TrackingRegistry.unregister_calls

    def test_default_is_noop(self):
        HookTestRegistry.register(AlphaImpl)
        # Should not raise
        HookTestRegistry.unregister("alpha")
        assert "alpha" not in HookTestRegistry.implementations


class TestHookInteraction:
    """Tests for hooks interacting with other registry features."""

    def test_works_with_hierarchical_registry(self):
        class ParentReg(Registry):
            implementations_module = "parent_hook_impls"

        class ChildReg(HierarchicalRegistry):
            implementations_module = "child_hook_impls"
            parent_registry = ParentReg
            register_calls: list = []

            @classmethod
            def on_register(cls, slug, implementation, meta):
                cls.register_calls.append(slug)

        ChildReg.implementations = {}
        ChildReg.register_calls = []

        class ChildImpl(HookTestInterface):
            slug = "child_impl"

        ChildReg.register(ChildImpl)
        assert "child_impl" in ChildReg.register_calls

    def test_validate_failure_skips_later_hooks(self):
        class StrictRegistry(Registry):
            implementations_module = "strict_hook_impls"
            on_register_called: bool = False

            @classmethod
            def validate_implementation(cls, implementation):
                raise ValueError("Rejected")

            @classmethod
            def on_register(cls, slug, implementation, meta):
                cls.on_register_called = True

        StrictRegistry.implementations = {}
        StrictRegistry.on_register_called = False

        with pytest.raises(ValueError, match="Rejected"):
            StrictRegistry.register(AlphaImpl)

        assert StrictRegistry.on_register_called is False
        assert not StrictRegistry.implementations

    def test_register_decorator_triggers_hooks(self):
        class DecoratorRegistry(Registry):
            implementations_module = "decorator_impls"
            register_calls: list = []

            @classmethod
            def on_register(cls, slug, implementation, meta):
                cls.register_calls.append(slug)

        DecoratorRegistry.implementations = {}
        DecoratorRegistry.register_calls = []

        @register(DecoratorRegistry)
        class DecoratedImpl(HookTestInterface):
            slug = "decorated"

        assert "decorated" in DecoratorRegistry.register_calls
        assert "decorated" in DecoratorRegistry.implementations

    def test_interface_init_subclass_triggers_hooks(self):
        class AutoRegistry(Registry):
            implementations_module = "auto_impls"
            register_calls: list = []

            @classmethod
            def on_register(cls, slug, implementation, meta):
                cls.register_calls.append(slug)

        AutoRegistry.implementations = {}
        AutoRegistry.register_calls = []

        class AutoInterface(Interface):
            registry = AutoRegistry
            slug = "auto"

        assert "auto" in AutoRegistry.register_calls

    def test_custom_meta_available_in_on_register(self):
        class EnrichedRegistry(Registry):
            implementations_module = "enriched_impls"
            captured_meta: dict = {}

            @classmethod
            def build_implementation_meta(cls, implementation):
                meta = super().build_implementation_meta(implementation)
                meta["registered_at"] = "2026-02-14"
                return meta

            @classmethod
            def on_register(cls, slug, implementation, meta):
                cls.captured_meta = dict(meta)

        EnrichedRegistry.implementations = {}
        EnrichedRegistry.captured_meta = {}

        EnrichedRegistry.register(AlphaImpl)
        assert EnrichedRegistry.captured_meta["registered_at"] == "2026-02-14"
        assert EnrichedRegistry.captured_meta["klass"] is AlphaImpl

    def test_custom_meta_available_in_on_unregister(self):
        class EnrichedRegistry(Registry):
            implementations_module = "enriched_impls2"
            captured_meta: dict = {}

            @classmethod
            def build_implementation_meta(cls, implementation):
                meta = super().build_implementation_meta(implementation)
                meta["tag"] = "important"
                return meta

            @classmethod
            def on_unregister(cls, slug, meta):
                cls.captured_meta = dict(meta)

        EnrichedRegistry.implementations = {}
        EnrichedRegistry.captured_meta = {}

        EnrichedRegistry.register(AlphaImpl)
        EnrichedRegistry.unregister("alpha")
        assert EnrichedRegistry.captured_meta["tag"] == "important"


class TestBackwardCompatibility:
    """Tests that existing register/unregister behavior is unchanged."""

    def test_register_stores_implementation(self):
        HookTestRegistry.register(AlphaImpl)
        assert "alpha" in HookTestRegistry.implementations
        assert HookTestRegistry.implementations["alpha"]["klass"] is AlphaImpl

    def test_register_emits_signal(self):
        received = []

        def handler(sender, **kwargs):
            received.append(kwargs)

        implementation_registered.connect(handler)
        try:
            HookTestRegistry.register(AlphaImpl)
            assert len(received) == 1
            assert received[0]["implementation"] is AlphaImpl
        finally:
            implementation_registered.disconnect(handler)

    def test_unregister_removes_implementation(self):
        HookTestRegistry.register(AlphaImpl)
        HookTestRegistry.unregister("alpha")
        assert "alpha" not in HookTestRegistry.implementations

    def test_unregister_emits_signal(self):
        received = []

        def handler(sender, **kwargs):
            received.append(kwargs)

        implementation_unregistered.connect(handler)
        try:
            HookTestRegistry.register(AlphaImpl)
            HookTestRegistry.unregister("alpha")
            assert len(received) == 1
            assert received[0]["slug"] == "alpha"
        finally:
            implementation_unregistered.disconnect(handler)

    def test_unregister_missing_raises(self):
        with pytest.raises(ImplementationNotFound):
            HookTestRegistry.unregister("nonexistent")

    def test_register_no_slug_raises(self):
        class NoSlug(HookTestInterface):
            pass

        with pytest.raises(ValueError):
            HookTestRegistry.register(NoSlug)

    def test_register_wrong_interface_raises(self):
        class TypedRegistry(Registry):
            implementations_module = "typed_impls"
            interface_class = HookTestInterface

        TypedRegistry.implementations = {}

        class Wrong:
            slug = "wrong"

        with pytest.raises(TypeError):
            TypedRegistry.register(Wrong)

    def test_implementation_meta_default_keys(self):
        HookTestRegistry.register(AlphaImpl)
        meta = HookTestRegistry.implementations["alpha"]
        assert set(meta.keys()) == {"klass", "description", "icon", "priority"}

    def test_multiple_register_unregister_cycles(self):
        HookTestRegistry.register(AlphaImpl)
        HookTestRegistry.register(BetaImpl)
        assert len(HookTestRegistry.implementations) == 2

        HookTestRegistry.unregister("alpha")
        assert len(HookTestRegistry.implementations) == 1
        assert "beta" in HookTestRegistry.implementations

        HookTestRegistry.unregister("beta")
        assert len(HookTestRegistry.implementations) == 0
