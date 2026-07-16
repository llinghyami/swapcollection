"""Tests for SwapDict and SwapList."""

import os
import pytest
import tempfile
import pickle

from swapcollection import SwapDict, SwapList


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_db(monkeypatch):
    """Give each test its own SQLite files to avoid cross-test I/O conflicts."""
    for cls, attr in ((SwapDict, "PATH"), (SwapList, "PATH")):
        fd, path = tempfile.mkstemp(suffix=".db", prefix=f"swap_test_{cls.__name__}_")
        os.close(fd)
        monkeypatch.setattr(cls, attr, path)
    yield
    import gc; gc.collect()
    for cls in (SwapDict, SwapList):
        p = getattr(cls, "PATH")
        if os.path.exists(p):
            os.remove(p)


def SD(data=None, size_threshold=1048576):
    """Helper: build a SwapDict with a sensible default threshold."""
    return SwapDict(data or {}, size_threshold=size_threshold)


def SL(iterable=None, size_threshold=1048576):
    """Helper: build a SwapList with a sensible default threshold."""
    return SwapList(iterable, size_threshold=size_threshold)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestInit:
    def test_empty(self):
        d = SD()
        assert len(d) == 0

    def test_with_initial_data_small(self):
        d = SD({"a": 1, "b": "hello"}, size_threshold=10000)
        assert d["a"] == 1
        assert d["b"] == "hello"

    def test_with_initial_data_large_value(self):
        """Initial data with a value that exceeds threshold gets spilled."""
        big = b"x" * 5000
        d = SD({"big": big}, size_threshold=100)
        assert d["big"] == big
        assert len(d) == 1


# ---------------------------------------------------------------------------
# __setitem__ / __getitem__
# ---------------------------------------------------------------------------

class TestSetGetItem:
    def test_small_bytes_in_memory(self):
        d = SD(size_threshold=100)
        d["k"] = b"small"
        assert d["k"] == b"small"

    def test_large_bytes_spilled(self):
        d = SD(size_threshold=100)
        big = b"x" * 500
        d["k"] = big
        assert d["k"] == big  # transparent retrieval

    def test_small_string_in_memory(self):
        d = SD(size_threshold=100)
        d["k"] = "short"
        assert d["k"] == "short"

    def test_large_string_spilled(self):
        d = SD(size_threshold=100)
        big = "x" * 2000   # pickle ~2000+ bytes → should spill
        d["k"] = big
        assert d["k"] == big

    def test_int_value(self):
        """int has no len() — stays in memory regardless of size."""
        d = SD(size_threshold=1)
        d["k"] = 42
        assert d["k"] == 42

    def test_float_value(self):
        d = SD(size_threshold=1)
        d["k"] = 3.14
        assert d["k"] == 3.14

    def test_none_value(self):
        d = SD(size_threshold=1)
        d["k"] = None
        assert d["k"] is None

    def test_bool_value(self):
        d = SD(size_threshold=1)
        d["k"] = True
        assert d["k"] is True

    def test_small_dict_in_memory(self):
        d = SD(size_threshold=10000)
        d["k"] = {"a": 1, "b": "hello"}
        assert d["k"] == {"a": 1, "b": "hello"}

    def test_large_dict_spilled(self):
        d = SD(size_threshold=100)
        big_dict = {str(i): b"x" * 200 for i in range(50)}
        d["k"] = big_dict
        assert d["k"] == big_dict

    def test_nested_structure_spilled(self):
        d = SD(size_threshold=100)
        nested = {"level1": {"level2": {"level3": b"x" * 500}}}
        d["k"] = nested
        assert d["k"] == nested

    def test_list_spilled(self):
        d = SD(size_threshold=100)
        big_list = [b"x" * 200 for _ in range(20)]
        d["k"] = big_list
        assert d["k"] == big_list

    def test_overwrite_small_with_large(self):
        d = SD(size_threshold=100)
        d["k"] = "small"
        d["k"] = b"x" * 10000
        assert d["k"] == b"x" * 10000

    def test_overwrite_large_with_small(self):
        d = SD(size_threshold=100)
        d["k"] = b"x" * 10000
        d["k"] = "small"
        assert d["k"] == "small"

    def test_multiple_keys_some_spilled(self):
        d = SD(size_threshold=100)
        d["a"] = "tiny"
        d["b"] = b"x" * 5000
        d["c"] = 99
        d["d"] = {"big": b"y" * 5000}
        assert d["a"] == "tiny"
        assert d["b"] == b"x" * 5000
        assert d["c"] == 99
        assert d["d"] == {"big": b"y" * 5000}

    def test_missing_key_raises_keyerror(self):
        d = SD()
        with pytest.raises(KeyError):
            _ = d["nonexistent"]

    def test_spilled_value_not_corrupted(self):
        """Binary data round-trips perfectly."""
        d = SD(size_threshold=1)
        raw = bytes(range(256))
        d["k"] = raw
        assert d["k"] == raw


# ---------------------------------------------------------------------------
# __delitem__
# ---------------------------------------------------------------------------

class TestDelItem:
    def test_delete_small_value(self):
        d = SD(size_threshold=10000)
        d["k"] = "hello"
        del d["k"]
        assert "k" not in d

    def test_delete_spilled_value(self):
        d = SD(size_threshold=100)
        d["k"] = b"x" * 500
        del d["k"]
        assert "k" not in d

    def test_delete_nonexistent_raises_keyerror(self):
        d = SD()
        with pytest.raises(KeyError):
            del d["nope"]


# ---------------------------------------------------------------------------
# Dict-like interface
# ---------------------------------------------------------------------------

class TestDictInterface:
    def test_len(self):
        d = SD({"a": 1, "b": 2, "c": 3})
        assert len(d) == 3

    def test_contains(self):
        d = SD({"a": 1})
        assert "a" in d
        assert "b" not in d

    def test_keys(self):
        d = SD({"a": 1, "b": 2})
        assert set(d.keys()) == {"a", "b"}

    def test_values(self):
        d = SD(size_threshold=1)
        d["a"] = b"x" * 500  # spilled
        d["b"] = 42           # in-memory
        vals = list(d.values())
        assert b"x" * 500 in vals
        assert 42 in vals
        assert len(vals) == 2

    def test_items(self):
        d = SD(size_threshold=1)
        d["a"] = b"x" * 500
        d["b"] = 42
        items = dict(d.items())
        assert items["a"] == b"x" * 500
        assert items["b"] == 42

    def test_update(self):
        d = SD({"a": 1}, size_threshold=100)
        d.update({"b": b"x" * 500, "c": "hello"})
        assert d["b"] == b"x" * 500
        assert d["c"] == "hello"
        assert d["a"] == 1

    def test_get(self):
        d = SD({"a": 42}, size_threshold=1)
        old = {"key": b"x" * 500}
        d["spilled"] = old
        assert d.get("spilled") == old
        assert d.get("nonexistent") is None
        assert d.get("nonexistent", "default") == "default"

    def test_pop(self):
        d = SD({"a": 1, "spilled": b"x" * 500}, size_threshold=100)
        val = d.pop("spilled")
        assert val == b"x" * 500
        assert "spilled" not in d

    def test_popitem(self):
        d = SD({"a": b"x" * 500}, size_threshold=100)
        k, v = d.popitem()
        assert k == "a"
        assert v == b"x" * 500
        assert len(d) == 0

    def test_clear(self):
        d = SD(size_threshold=100)
        d["a"] = b"x" * 500
        d["b"] = 42
        d.clear()
        assert len(d) == 0

    def test_setdefault_new_key(self):
        d = SD({"a": b"x" * 500}, size_threshold=100)
        val = d.setdefault("b", "default")
        assert val == "default"
        assert d["b"] == "default"

    def test_setdefault_existing_key(self):
        d = SD(size_threshold=100)
        d["a"] = b"x" * 500
        val = d.setdefault("a", "never used")
        assert val == b"x" * 500

    def test_copy(self):
        d = SD(size_threshold=100)
        d["a"] = b"x" * 500
        d["b"] = 42
        c = d.copy()
        assert c["a"] == b"x" * 500
        assert c["b"] == 42
        c["a"] = "changed"
        assert d["a"] == b"x" * 500  # original unchanged


# ---------------------------------------------------------------------------
# Boundary conditions
# ---------------------------------------------------------------------------

class TestBoundary:
    @staticmethod
    def _is_spilled(d, key):
        val = d.data[key]
        return isinstance(val, str) and val.startswith(SwapDict.PREFIX)

    def test_exactly_at_threshold_spilled(self):
        """len(pickle.dumps(value)) == size_threshold → spilled (>=)."""
        target = b"x" * 999
        thresh = len(pickle.dumps(target))
        d = SD(size_threshold=thresh)
        d["k"] = target
        assert self._is_spilled(d, "k")

    def test_one_byte_below_threshold_not_spilled(self):
        target = b"x" * 1000
        thresh = len(pickle.dumps(target)) + 1
        d = SD(size_threshold=thresh)
        d["k"] = target
        assert not self._is_spilled(d, "k")

    def test_threshold_zero_everything_spilled(self):
        d = SD(size_threshold=0)
        d["a"] = b""
        assert self._is_spilled(d, "a")
        assert d["a"] == b""


# ---------------------------------------------------------------------------
# SwapList
# ---------------------------------------------------------------------------

class TestSwapListInit:
    def test_empty(self):
        assert len(SL()) == 0

    def test_from_iterable(self):
        xs = SL([1, 2, 3])
        assert list(xs) == [1, 2, 3]

    def test_from_iterable_with_spill(self):
        xs = SL([b"x" * 500], size_threshold=100)
        assert xs[0] == b"x" * 500


class TestSwapListSetGet:
    def test_small_int(self):
        xs = SL([1, 2, 3])
        assert xs[0] == 1 and xs[1] == 2 and xs[2] == 3

    def test_large_bytes_spilled(self):
        xs = SL(size_threshold=100)
        xs.append(b"x" * 500)
        assert xs[0] == b"x" * 500

    def test_large_dict_spilled(self):
        xs = SL(size_threshold=100)
        xs.append({str(i): b"x" * 200 for i in range(20)})
        assert len(xs[0]) == 20

    def test_setitem_existing(self):
        xs = SL([1, 2, 3], size_threshold=1)
        xs[1] = b"x" * 500
        assert xs[1] == b"x" * 500

    def test_mixed_spilled_and_in_memory(self):
        xs = SL(size_threshold=100)
        xs.append(42)
        xs.append(b"x" * 500)
        xs.append("hello")
        assert xs[0] == 42
        assert xs[1] == b"x" * 500
        assert xs[2] == "hello"

    def test_int_value(self):
        xs = SL(size_threshold=1)
        xs.append(99)
        assert xs[0] == 99

    def test_none_value(self):
        xs = SL(size_threshold=1)
        xs.append(None)
        assert xs[0] is None

    def test_bool_value(self):
        xs = SL(size_threshold=1)
        xs.append(True)
        assert xs[0] is True


class TestSwapListInsert:
    def test_insert_beginning(self):
        xs = SL([2, 3], size_threshold=100)
        xs.insert(0, b"x" * 500)
        assert xs[0] == b"x" * 500
        assert xs[1] == 2
        assert xs[2] == 3

    def test_insert_middle(self):
        xs = SL([1, 3], size_threshold=100)
        xs.insert(1, b"x" * 500)
        assert xs[1] == b"x" * 500


class TestSwapListDelete:
    def test_delete_item(self):
        xs = SL([1, b"x" * 500, 3], size_threshold=100)
        del xs[1]
        assert list(xs) == [1, 3]

    def test_pop(self):
        xs = SL(size_threshold=100)
        xs.append(b"x" * 500)
        val = xs.pop()
        assert val == b"x" * 500
        assert len(xs) == 0

    def test_pop_index(self):
        xs = SL([1, b"x" * 500, 3], size_threshold=100)
        val = xs.pop(1)
        assert val == b"x" * 500


class TestSwapListExtend:
    def test_extend(self):
        xs = SL([1], size_threshold=100)
        xs.extend([b"x" * 500, b"y" * 500])
        assert xs[1] == b"x" * 500
        assert xs[2] == b"y" * 500

    def test_extend_swap_list(self):
        xs = SL([1, 2], size_threshold=100)
        ys = SL([b"x" * 500], size_threshold=100)
        xs.extend(ys)
        assert xs[2] == b"x" * 500


class TestSwapListOperators:
    def test_add(self):
        xs = SL([1, 2], size_threshold=100)
        ys = SL([b"x" * 500], size_threshold=100)
        zs = xs + ys
        assert zs[0] == 1
        assert zs[2] == b"x" * 500

    def test_iadd(self):
        xs = SL([1], size_threshold=100)
        xs += [b"x" * 500]
        assert xs[0] == 1
        assert xs[1] == b"x" * 500

    def test_mul(self):
        xs = SL([b"x" * 500], size_threshold=100)
        ys = xs * 3
        assert len(ys) == 3
        assert ys[0] == b"x" * 500
        assert ys[2] == b"x" * 500

    def test_imul(self):
        xs = SL([1], size_threshold=100)
        xs *= 3
        assert list(xs) == [1, 1, 1]


class TestSwapListContains:
    def test_contains_small(self):
        xs = SL([1, 2, 3])
        assert 2 in xs
        assert 99 not in xs

    def test_contains_spilled(self):
        xs = SL(size_threshold=100)
        val = b"x" * 500
        xs.append(val)
        assert val in xs


class TestSwapListLen:
    def test_len(self):
        xs = SL([1, 2, 3], size_threshold=100)
        assert len(xs) == 3

    def test_len_after_append_spilled(self):
        xs = SL(size_threshold=100)
        xs.append(b"x" * 500)
        assert len(xs) == 1


class TestSwapListCopy:
    def test_copy(self):
        xs = SL([1, b"x" * 500], size_threshold=100)
        ys = xs.copy()
        assert ys[0] == 1
        assert ys[1] == b"x" * 500
        ys[0] = 99
        assert xs[0] == 1  # independent


class TestSwapListClear:
    def test_clear(self):
        xs = SL([1, b"x" * 500], size_threshold=100)
        xs.clear()
        assert len(xs) == 0


class TestSwapListIndex:
    def test_index(self):
        xs = SL([1, b"x" * 500, 3], size_threshold=100)
        assert xs.index(3) == 2

    def test_index_spilled_value(self):
        val = b"x" * 500
        xs = SL([1, val, 3], size_threshold=100)
        assert xs.index(val) == 1


class TestSwapListCount:
    def test_count(self):
        val = b"x" * 500
        xs = SL([val, 1, val], size_threshold=100)
        assert xs.count(val) == 2


class TestSwapListRemove:
    def test_remove(self):
        xs = SL([1, b"x" * 500, 3], size_threshold=100)
        xs.remove(b"x" * 500)
        assert list(xs) == [1, 3]

    def test_remove_not_found(self):
        xs = SL([1, 2], size_threshold=100)
        with pytest.raises(ValueError):
            xs.remove(b"x" * 500)


class TestSwapListReverse:
    def test_reverse(self):
        xs = SL([1, b"x" * 500, 3], size_threshold=100)
        xs.reverse()
        assert xs[0] == 3
        assert xs[2] == 1


class TestSwapListSort:
    def test_sort_smalls(self):
        xs = SL([3, 1, 2])
        xs.sort()
        assert list(xs) == [1, 2, 3]

    def test_sort_by_key(self):
        xs = SL([{"n": 2}, {"n": 1}], size_threshold=1)
        xs.sort(key=lambda x: x["n"])
        assert xs[0]["n"] == 1
        assert xs[1]["n"] == 2


class TestSwapListBoundary:
    @staticmethod
    def _is_spilled(xs, i):
        val = xs.data[i]
        return isinstance(val, str) and val.startswith(SwapList.PREFIX)

    def test_exactly_at_threshold_spilled(self):
        target = b"x" * 999
        thresh = len(pickle.dumps(target))
        xs = SL(size_threshold=thresh)
        xs.append(target)
        assert self._is_spilled(xs, 0)

    def test_one_byte_below_threshold_not_spilled(self):
        target = b"x" * 1000
        thresh = len(pickle.dumps(target)) + 1
        xs = SL(size_threshold=thresh)
        xs.append(target)
        assert not self._is_spilled(xs, 0)

    def test_threshold_zero_everything_spilled(self):
        xs = SL(size_threshold=0)
        xs.append(b"")
        assert self._is_spilled(xs, 0)
        assert xs[0] == b""


# ---------------------------------------------------------------------------
# SwapDict: __iter__, __reversed__
# ---------------------------------------------------------------------------

class TestSwapDictIteration:
    def test_iter_keys(self):
        d = SD({"a": 1, "b": 2, "c": 3})
        assert set(iter(d)) == {"a", "b", "c"}

    def test_iter_with_spilled_values(self):
        d = SD(size_threshold=100)
        d["x"] = b"x" * 500
        d["y"] = 42
        d["z"] = "hello"
        assert set(iter(d)) == {"x", "y", "z"}

    def test_reversed(self):
        """UserDict does not support reversed(); iteration order is insertion order."""
        d = SD({"a": 1, "b": 2, "c": 3})
        keys = [k for k in d]
        assert keys == ["a", "b", "c"]

    def test_list_conversion(self):
        d = SD({"a": 1, "b": 2, "c": 3})
        assert sorted(d) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# SwapDict: __repr__
# ---------------------------------------------------------------------------

class TestSwapDictRepr:
    def test_repr_all_in_memory(self):
        d = SD({"a": 1, "b": "hello"})
        r = repr(d)
        assert "'a': 1" in r
        assert "'b': 'hello'" in r

    def test_repr_with_spilled_values(self):
        d = SD(size_threshold=100)
        d["k"] = b"x" * 500
        r = repr(d)
        assert "k" in r
        assert repr(b"x" * 500) in r  # value should be resolved

    def test_repr_empty(self):
        assert repr(SD()) == "{}"


# ---------------------------------------------------------------------------
# SwapDict: __eq__
# ---------------------------------------------------------------------------

class TestSwapDictEquality:
    def test_eq_regular_dict(self):
        d = SD({"a": 1, "b": 2})
        assert d == {"a": 1, "b": 2}

    def test_eq_swap_dict(self):
        d1 = SD({"a": 1, "b": 2})
        d2 = SD({"a": 1, "b": 2})
        assert d1 == d2

    def test_eq_with_spilled_values(self):
        d1 = SD(size_threshold=100)
        d2 = SD(size_threshold=100)
        val = b"x" * 500
        d1["k"] = val
        d2["k"] = val
        assert d1 == d2

    def test_eq_with_regular_dict_spilled(self):
        d = SD(size_threshold=100)
        val = b"x" * 500
        d["k"] = val
        assert d == {"k": val}

    def test_not_equal(self):
        d = SD({"a": 1})
        assert d != {"a": 2}
        assert d != {}


# ---------------------------------------------------------------------------
# SwapDict: update variants
# ---------------------------------------------------------------------------

class TestSwapDictUpdate:
    def test_update_with_kwargs(self):
        d = SD(size_threshold=100)
        big = b"x" * 500
        d.update(a=1, b=big)
        assert d["a"] == 1
        assert d["b"] == big

    def test_update_with_swap_dict(self):
        d1 = SD(size_threshold=100)
        d1["a"] = b"x" * 500
        d2 = SD(size_threshold=100)
        d2.update(d1)
        assert d2["a"] == b"x" * 500

    def test_update_overwrites_existing(self):
        d = SD(size_threshold=100)
        d["k"] = "old"
        d.update(k=b"x" * 500)
        assert d["k"] == b"x" * 500

    def test_update_empty(self):
        d = SD({"a": 1})
        d.update({})
        assert d["a"] == 1
        assert len(d) == 1


# ---------------------------------------------------------------------------
# SwapDict: fromkeys
# ---------------------------------------------------------------------------

class TestSwapDictFromKeys:
    def test_fromkeys_simple(self):
        d = SwapDict.fromkeys(["a", "b", "c"], 42)
        assert d["a"] == 42
        assert d["b"] == 42
        assert d["c"] == 42
        assert len(d) == 3

    def test_fromkeys_spilled_default(self):
        big = b"x" * 500
        d = SwapDict.fromkeys(["k"], big)
        assert d["k"] == big


# ---------------------------------------------------------------------------
# SwapDict: __or__ / __ior__ / __ror__  (Python 3.9+)
# ---------------------------------------------------------------------------

class TestSwapDictMerge:
    def test_or_with_dict(self):
        d = SD({"a": 1}, size_threshold=100)
        big = b"x" * 500
        merged = d | {"b": big}
        assert merged["a"] == 1
        assert merged["b"] == big

    def test_ior_with_dict(self):
        d = SD(size_threshold=100)
        big = b"x" * 500
        d |= {"a": 1, "b": big}
        assert d["a"] == 1
        assert d["b"] == big


# ---------------------------------------------------------------------------
# SwapDict: iteration helpers with spilled values
# ---------------------------------------------------------------------------

class TestSwapDictIterHelpers:
    def test_keys_all_spilled(self):
        d = SD(size_threshold=100)
        d["a"] = b"x" * 500
        d["b"] = b"y" * 500
        assert set(d.keys()) == {"a", "b"}

    def test_values_all_spilled(self):
        d = SD(size_threshold=100)
        d["a"] = b"x" * 500
        d["b"] = b"y" * 500
        vals = list(d.values())
        assert len(vals) == 2
        assert b"x" * 500 in vals
        assert b"y" * 500 in vals

    def test_items_all_spilled(self):
        d = SD(size_threshold=100)
        d["a"] = b"x" * 500
        d["b"] = 42
        items = list(d.items())
        assert ("a", b"x" * 500) in items
        assert ("b", 42) in items

    def test_items_are_independent(self):
        """items() returns resolved copies, not live references."""
        d = SD(size_threshold=100)
        d["k"] = b"x" * 500
        for _k, v in d.items():
            pass
        assert d["k"] == b"x" * 500  # still accessible


# ---------------------------------------------------------------------------
# SwapDict: integer / tuple keys (not just strings)
# ---------------------------------------------------------------------------

class TestSwapDictKeyTypes:
    def test_int_keys(self):
        d = SD(size_threshold=100)
        d[1] = "one"
        d[2] = b"x" * 500
        assert d[1] == "one"
        assert d[2] == b"x" * 500

    def test_tuple_keys(self):
        d = SD(size_threshold=100)
        d[(1, 2)] = "value"
        assert d[(1, 2)] == "value"


# ---------------------------------------------------------------------------
# SwapList: slice operations
# ---------------------------------------------------------------------------

class TestSwapListSlice:
    def test_get_slice_in_memory(self):
        xs = SL([1, 2, 3, 4, 5])
        assert xs[1:4] == [2, 3, 4]

    def test_get_slice_with_spilled(self):
        xs = SL(size_threshold=100)
        xs.extend([1, b"x" * 500, 3, b"y" * 500, 5])
        sl = xs[1:4]
        assert sl[0] == b"x" * 500
        assert sl[1] == 3
        assert sl[2] == b"y" * 500
        assert len(sl) == 3

    def test_get_slice_step(self):
        xs = SL([1, 2, 3, 4, 5])
        assert xs[::2] == [1, 3, 5]

    def test_get_slice_negative(self):
        xs = SL([1, 2, 3, 4, 5])
        assert xs[-3:-1] == [3, 4]

    def test_set_slice_with_list(self):
        xs = SL([1, 2, 3, 4, 5])
        xs[1:4] = [99, 100]
        assert list(xs) == [1, 99, 100, 5]

    def test_set_slice_with_spilled(self):
        xs = SL([1, 2, 3], size_threshold=100)
        xs[1:2] = [b"x" * 500, b"y" * 500]
        assert xs[0] == 1
        assert xs[1] == b"x" * 500
        assert xs[2] == b"y" * 500
        assert xs[3] == 3

    def test_del_slice(self):
        xs = SL([1, 2, 3, 4, 5])
        del xs[1:3]
        assert list(xs) == [1, 4, 5]

    def test_get_slice_empty(self):
        xs = SL([1, 2, 3])
        assert xs[5:10] == []


# ---------------------------------------------------------------------------
# SwapList: __eq__
# ---------------------------------------------------------------------------

class TestSwapListEquality:
    def test_eq_regular_list(self):
        xs = SL([1, 2, 3])
        assert xs == [1, 2, 3]

    def test_eq_swap_list(self):
        xs1 = SL([1, 2, 3])
        xs2 = SL([1, 2, 3])
        assert xs1 == xs2

    def test_eq_with_spilled(self):
        xs1 = SL(size_threshold=100)
        xs2 = SL(size_threshold=100)
        xs1.extend([1, b"x" * 500])
        xs2.extend([1, b"x" * 500])
        assert xs1 == xs2

    def test_eq_regular_list_spilled(self):
        xs = SL(size_threshold=100)
        xs.extend([1, b"x" * 500])
        assert xs == [1, b"x" * 500]

    def test_not_equal(self):
        xs = SL([1, 2, 3])
        assert xs != [1, 2]
        assert xs != [1, 2, 4]


# ---------------------------------------------------------------------------
# SwapList: __repr__
# ---------------------------------------------------------------------------

class TestSwapListRepr:
    def test_repr_in_memory(self):
        xs = SL([1, "hello", 3])
        r = repr(xs)
        assert "1" in r and "hello" in r and "3" in r

    def test_repr_with_spilled(self):
        xs = SL(size_threshold=100)
        xs.append(b"x" * 500)
        r = repr(xs)
        assert repr(b"x" * 500) in r

    def test_repr_empty(self):
        assert repr(SL()) == "[]"


# ---------------------------------------------------------------------------
# SwapList: __radd__
# ---------------------------------------------------------------------------

class TestSwapListRAdd:
    def test_radd_regular_list(self):
        xs = SL([3, 4], size_threshold=100)
        ys = [1, 2] + xs
        assert ys == [1, 2, 3, 4]

    def test_radd_with_spilled(self):
        xs = SL(size_threshold=100)
        xs.append(b"x" * 500)
        ys = [1] + xs
        assert ys[0] == 1
        assert ys[1] == b"x" * 500


# ---------------------------------------------------------------------------
# SwapList: negative indexing
# ---------------------------------------------------------------------------

class TestSwapListNegativeIndex:
    def test_get_negative(self):
        xs = SL([1, 2, 3])
        assert xs[-1] == 3
        assert xs[-2] == 2
        assert xs[-3] == 1

    def test_get_negative_spilled(self):
        xs = SL(size_threshold=100)
        xs.extend([1, b"x" * 500, 3])
        assert xs[-1] == 3
        assert xs[-2] == b"x" * 500
        assert xs[-3] == 1

    def test_set_negative(self):
        xs = SL([1, 2, 3], size_threshold=100)
        xs[-1] = b"x" * 500
        assert xs[-1] == b"x" * 500


# ---------------------------------------------------------------------------
# SwapList: insert spilled at various positions
# ---------------------------------------------------------------------------

class TestSwapListInsertVariants:
    def test_insert_end_large(self):
        xs = SL([1, 2], size_threshold=100)
        xs.insert(2, b"x" * 500)
        assert xs[2] == b"x" * 500
        assert len(xs) == 3

    def test_insert_negative(self):
        xs = SL([1, 2, 3], size_threshold=100)
        xs.insert(-1, b"x" * 500)  # before 3
        assert xs[-2] == b"x" * 500
        assert xs[-1] == 3


# ---------------------------------------------------------------------------
# SwapList: sort with mixed spilled + in-memory
# ---------------------------------------------------------------------------

class TestSwapListSortVariants:
    def test_sort_with_spilled_values(self):
        xs = SL(size_threshold=100)
        xs.extend([b"c" * 500, b"a" * 500, b"b" * 500])
        xs.sort()
        assert xs[0] == b"a" * 500
        assert xs[1] == b"b" * 500
        assert xs[2] == b"c" * 500

    def test_sort_reverse(self):
        xs = SL([3, 1, 2])
        xs.sort(reverse=True)
        assert list(xs) == [3, 2, 1]


# ---------------------------------------------------------------------------
# SwapList: append / extend edge cases
# ---------------------------------------------------------------------------

class TestSwapListAppendExtend:
    def test_append_multiple_spilled(self):
        xs = SL(size_threshold=100)
        xs.append(b"x" * 500)
        xs.append(b"y" * 500)
        xs.append(b"z" * 500)
        assert xs[0] == b"x" * 500
        assert xs[1] == b"y" * 500
        assert xs[2] == b"z" * 500
        assert len(xs) == 3

    def test_extend_empty(self):
        xs = SL([1, 2, 3])
        xs.extend([])
        assert list(xs) == [1, 2, 3]

    def test_extend_generator(self):
        xs = SL(size_threshold=100)
        def gen():
            yield 1
            yield b"x" * 500
            yield 2
        xs.extend(gen())
        assert xs[0] == 1
        assert xs[1] == b"x" * 500
        assert xs[2] == 2


# ---------------------------------------------------------------------------
# SwapList: __delitem__ slice
# ---------------------------------------------------------------------------

class TestSwapListDelSlice:
    def test_del_slice_with_spilled(self):
        xs = SL(size_threshold=100)
        xs.extend([1, b"x" * 500, b"y" * 500, 4])
        del xs[1:3]
        assert list(xs) == [1, 4]

    def test_del_all(self):
        xs = SL([1, 2, 3])
        del xs[:]
        assert len(xs) == 0
