import sys
from abc import ABCMeta
from collections.abc import Hashable
from typing import Any, TypeVar
from weakref import WeakKeyDictionary, ref

from .metrics import COUNTERS

counter = COUNTERS[__name__]

_V = TypeVar("_V", bound=Hashable)
_INTERN: WeakKeyDictionary[Hashable, ref[Hashable]] = WeakKeyDictionary()


def intern(x: _V) -> _V:
    """Return a canonical object for `x`, useful for hash consing."""
    counter["intern.hit"] += 1
    if x is None or x is False or x is True:
        return x  # type: ignore
    if isinstance(x, str):
        return sys.intern(x)  # type: ignore
    try:
        return _INTERN[x]()  # type: ignore
    except KeyError:
        counter["intern.hit"] -= 1
        counter["intern.miss"] += 1
        _INTERN[x] = ref(x)
        return x


class WeakHashConsMeta(ABCMeta):
    """Metaclass to hash cons instances."""

    def __call__(cls, *args, **kwargs):
        return intern(super().__call__(*args, **kwargs))

    def __new__(mcs, name, bases, namespace):
        # Support copy.deepcopy(-).
        def __deepcopy__(self, memo):
            return self

        # Support pickle.loads(pickle.dumps(-)) for dataclasses.
        def __reduce__(self):
            args = tuple(getattr(self, f) for f in self.__dataclass_fields__)
            return type(self), args

        namespace["__deepcopy__"] = __deepcopy__
        namespace["__reduce__"] = __reduce__
        return super().__new__(mcs, name, bases, namespace)

    def __getitem__(self, params):
        """Binding a generic type has no runtime effect."""
        return self


class HashConsArgsMeta(ABCMeta):
    """Metaclass to hash cons instances."""

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._cache: dict[tuple, Any] = {}

    def __call__(cls, *args):
        try:
            return cls._cache[args]
        except KeyError:
            obj = super().__call__(*args)
            cls._cache[args] = obj
            return obj

    def __new__(mcs, name, bases, namespace):
        # Support copy.deepcopy(-).
        def __deepcopy__(self, memo):
            return self

        # Support pickle.loads(pickle.dumps(-)) for dataclasses.
        def __reduce__(self):
            args = tuple(getattr(self, f) for f in self.__dataclass_fields__)
            return type(self), args

        namespace["__deepcopy__"] = __deepcopy__
        namespace["__reduce__"] = __reduce__
        return super().__new__(mcs, name, bases, namespace)
