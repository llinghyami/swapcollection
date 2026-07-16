"""Comprehensive tests for SwapList.__eq__ (and SwapDict.__eq__ by implication)."""

import os
import pytest
import tempfile
import pickle
from collections import UserList

from swapcollection import SwapDict, SwapList


# ---------------------------------------------------------------------------
# Fixtures (isolated DB per test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch):
    for cls, attr in ((SwapDict, "PATH"), (SwapList, "PATH")):
        fd, path = tempfile.mkstemp(suffix=".db", prefix=f"eq_test_{cls.__name__}_")
        os.close(fd)
        monkeypatch.setattr(cls, attr, path)
    yield
    import gc; gc.collect()
    for cls in (SwapDict, SwapList):
        p = getattr(cls, "PATH")
        if os.path.exists(p):
            os.remove(p)


def SL(iterable=None, size_threshold=100):
    return SwapList(iterable, size_threshold=size_threshold)


# ===================================================================
# SwapList __eq__
# ===================================================================

class TestSwapListEqBasic:
    """Fundamental equality/inequality cases."""

    def test_empty_vs_empty(self):
        assert SL() == SL()
        assert SL() == []

    def test_self_equality(self):
        xs = SL([1, 2, 3])
        assert xs == xs

    def test_same_in_memory_content(self):
        assert SL([1, 2, 3]) == SL([1, 2, 3])

    def test_different_length_not_equal(self):
        assert SL([1, 2]) != SL([1, 2, 3])

    def test_different_values_not_equal(self):
        assert SL([1, 2, 3]) != SL([1, 2, 4])

    def test_vs_regular_list(self):
        assert SL([1, 2, 3]) == [1, 2, 3]

    def test_vs_tuple(self):
        """SwapList should equal a tuple with same elements."""
        assert SL([1, 2, 3]) == (1, 2, 3)

    def test_not_equal_to_non_sequence(self):
        assert SL([1, 2, 3]) != 123
        assert SL([1, 2, 3]) != "hello"
        assert SL([1, 2, 3]) != {"a": 1}


class TestSwapListEqSpilled:
    """Equality when spilled values are involved."""

    def test_both_same_spilled(self):
        xs1 = SL([b"x" * 500, 42])
        xs2 = SL([b"x" * 500, 42])
        assert xs1 == xs2

    def test_different_spill_ids_still_equal(self):
        """Same logical content, different DB instances → different UUIDs."""
        xs1 = SL([b"x" * 500])
        xs2 = SL([b"x" * 500])
        assert xs1 == xs2  # resolved values equal regardless of UUID

    def test_spilled_vs_in_memory_equal(self):
        """Same value: spilled in one, in-memory in the other."""
        same = b"small"
        thresh = len(pickle.dumps(same)) + 1  # below threshold
        xs1 = SL([same], size_threshold=1)     # spills (pickle size >= 1)
        xs2 = SL([same], size_threshold=thresh) # keeps in memory
        assert xs1 == xs2

    def test_mixed_spilled_and_in_memory(self):
        xs1 = SL([1, b"x" * 500, "hello", b"y" * 500], size_threshold=100)
        xs2 = SL([1, b"x" * 500, "hello", b"y" * 500], size_threshold=100)
        assert xs1 == xs2

    def test_partially_spilled_partially_not(self):
        thresh = 200
        xs1 = SL([b"a" * 50, b"b" * 500, b"c" * 30, b"d" * 500], size_threshold=thresh)
        xs2 = SL([b"a" * 50, b"b" * 500, b"c" * 30, b"d" * 500], size_threshold=thresh)
        assert xs1 == xs2


class TestSwapListEqEdge:
    """Edge cases for equality."""

    def test_single_element(self):
        assert SL([42]) == [42]
        assert SL([b"x" * 500]) == [b"x" * 500]

    def test_none_values(self):
        assert SL([None]) == SL([None])
        assert SL([None, b"x" * 500]) == [None, b"x" * 500]

    def test_nested_structures(self):
        val = {"deep": [1, {2: b"x" * 500}]}
        assert SL([val]) == SL([val])

    def test_threshold_zero(self):
        xs1 = SL([b"x" * 500], size_threshold=0)
        xs2 = SL([b"x" * 500], size_threshold=0)
        assert xs1 == xs2

    def test_after_clear(self):
        xs = SL([1, 2, 3])
        xs.clear()
        assert xs == []

    def test_after_mutation_both_ways(self):
        xs = SL([1, 2])
        xs.append(3)
        ys = SL([1, 2, 3])
        assert xs == ys

    def test_non_list_iterable(self):
        """Comparing with a UserList or custom sequence."""
        from collections import UserList
        xs = SL([1, 2])
        ul = UserList([1, 2])
        assert xs == ul

    def test_range(self):
        """range is a Sequence but not a list."""
        xs = SL([0, 1, 2, 3, 4])
        assert xs == range(5)

    def test_generator(self):
        """Generator is NOT a Sequence, element-by-element comparison."""
        xs = SL([1, 2, 3])
        def gen():
            yield 1; yield 2; yield 3
        assert xs == list(gen())

    def test_chained_equality(self):
        xs = SL([1, 2])
        ys = SL([1, 2])
        zs = SL([1, 2])
        assert xs == ys == zs

    def test_transitivity_same_spilled(self):
        xs = SL([b"x" * 500])
        ys = SL([b"x" * 500])
        zs = SL([b"x" * 500])
        assert xs == ys == zs

    def test_bool_values(self):
        assert SL([True, False]) == SL([True, False])
        assert SL([True]) == [True]

    def test_mixed_types(self):
        assert SL([1, "a", 3.14, None, True, b"x" * 500]) == \
               SL([1, "a", 3.14, None, True, b"x" * 500])


class TestSwapListEqNegative:
    """Cases that MUST NOT be equal."""

    def test_one_spilled_one_not(self):
        """One side spills, other keeps same value in memory."""
        val = b"some moderately sized bytes"
        thresh = len(pickle.dumps(val))
        xs1 = SL([val], size_threshold=thresh)     # spills (>=)
        xs2 = SL([val], size_threshold=thresh + 1)  # in memory (<)
        assert xs1 == xs2  # same LOGICAL value → should still be equal

    def test_subclass_not_equal(self):
        class MyList(list):
            pass
        assert SL([1, 2]) != MyList([1, 2, 3])

    def test_different_order(self):
        """Same values, different order → not equal."""
        assert SL([1, 2, 3]) != SL([3, 2, 1])

    def test_empty_vs_nonempty(self):
        assert SL() != SL([1])
        assert SL() != [1]

    def test_after_pop(self):
        xs = SL([1, 2, 3])
        xs.pop()
        assert xs != [1, 2, 3]

    def test_after_insert(self):
        xs = SL([1, 3])
        xs.insert(1, 99)
        assert xs != [1, 3]


# ===================================================================
# SwapDict __eq__
# ===================================================================

class TestSwapDictEqBasic:
    def test_empty(self):
        assert SwapDict() == SwapDict()
        assert SwapDict() == {}

    def test_self(self):
        d = SwapDict({"a": 1})
        assert d == d

    def test_same_content(self):
        assert SwapDict({"a": 1, "b": 2}) == SwapDict({"a": 1, "b": 2})

    def test_vs_regular_dict(self):
        assert SwapDict({"a": 1}) == {"a": 1}

    def test_not_equal_different_keys(self):
        assert SwapDict({"a": 1}) != {"b": 1}

    def test_not_equal_different_values(self):
        assert SwapDict({"a": 1}) != {"a": 2}

    def test_not_equal_non_dict(self):
        assert SwapDict() != []
        assert SwapDict() != 0


class TestSwapDictEqSpilled:
    def test_both_spilled_same(self):
        d1 = SwapDict({"k": b"x" * 500}, size_threshold=100)
        d2 = SwapDict({"k": b"x" * 500}, size_threshold=100)
        assert d1 == d2

    def test_spilled_vs_in_memory(self):
        val = b"x" * 500
        thresh = 200
        d1 = SwapDict({"k": val}, size_threshold=thresh)     # spills
        d2 = {"k": val}                                       # plain dict
        assert d1 == d2

    def test_mixed(self):
        d1 = SwapDict(size_threshold=100)
        d1["a"] = 1
        d1["b"] = b"x" * 500
        d2 = SwapDict(size_threshold=100)
        d2["a"] = 1
        d2["b"] = b"x" * 500
        assert d1 == d2

    def test_after_update(self):
        d = SwapDict(size_threshold=100)
        d["k"] = b"x" * 500
        d.update({"k": 42})
        assert d == {"k": 42}

    def test_after_pop(self):
        d = SwapDict(size_threshold=100)
        d["k"] = b"x" * 500
        d.pop("k")
        assert d == {}
