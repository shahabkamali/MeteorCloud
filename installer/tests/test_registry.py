"""Registry and interface smoke tests."""

from __future__ import annotations

import pytest

from components.registry import get_component, list_components
from providers.registry import get_provider, list_providers


def test_aws_provider_is_registered() -> None:
    assert "aws" in list_providers()
    provider = get_provider("aws")
    assert provider.name == "aws"


def test_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="Unknown infrastructure provider"):
        get_provider("gcp")


def test_components_are_registered() -> None:
    names = list_components()
    assert names == ["postgres", "redis", "reverse_proxy"]


def test_component_methods_raise_not_implemented() -> None:
    component = get_component("postgres")
    with pytest.raises(NotImplementedError):
        component.validate()
