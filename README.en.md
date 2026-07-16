> **English** · [日本語 (Japanese)](README.md)

# swapcollection

A library that automatically offloads large objects stored in a
`dict`/`list` to SQLite, reducing memory usage. It can be used with
the same syntax as a regular `dict`/`list`.

## Quick Start

```bash
pip install swapcollection
```

### SwapDict

```python
from swapcollection import SwapDict

# Values whose pickled size >= size_threshold are spilled to SQLite
d = SwapDict(size_threshold=100)

# Small values stay in-memory
d["name"] = "alice"
d.data  # → {'name': 'alice'}

# Large values are transparently spilled to SQLite
d["blob"] = b"x" * 200
d.data  # → {'name': 'alice', 'blob': 'swapdict_<uuid>'}  (ID stored in memory)

# Retrieval works transparently — same as a normal dict
d["blob"]  # → b'xxxxxxxx...'

# All standard dict methods work
d.update({"a": 1, "b": 2})
len(d)             # → 4
list(d.keys())     # → ['name', 'blob', 'a', 'b']

d["name"]          # → 'alice'
d.get("missing")   # → None
d.pop("name")      # → 'alice'
"name" in d        # → False

d.setdefault("c", 99)  # → 99
list(d.items())
# → [('blob', b'xxx...'), ('a', 1), ('b', 2), ('c', 99)]

# repr() also resolves spilled values
repr(d)  # → "{'blob': b'xxx...', 'a': 1, 'b': 2, 'c': 99}"

# Class method
SwapDict.fromkeys(["x", "y"], 0)
# → {'x': 0, 'y': 0}

d.clear()
len(d)             # → 0
```

### SwapList

```python
from swapcollection import SwapList

# Same threshold concept
xs = SwapList(size_threshold=100)

xs.append(42)
xs.append(b"y" * 200)
xs[0]    # → 42
xs[1]    # → b'yyyyyy...'

xs.insert(1, "hello")
list(xs)  # → [42, 'hello', b'yyyyyy...']

xs.extend([1.5, b"z" * 200])
len(xs)   # → 5

# Slice access resolves spilled values
xs[1:3]   # → ['hello', b'yyyyyy...']

# Slice assignment with large values works
xs[2:4] = [99, b"w" * 200]

# contains / index / count
42 in xs             # → True
xs.index(42)         # → 0
xs.count(42)         # → 1

# pop
val = xs.pop()       # → b'zzzzzz...'
len(xs)              # → 4

# reverse
xs.reverse()

# sort (including spilled values)
ys = SwapList(size_threshold=50)
ys.extend([b"c" * 20, b"a" * 20, b"b" * 20])
ys.sort()
list(ys)  # → [b'aaaa...', b'bbbb...', b'cccc...']

# comparison works transparently
zs = SwapList([1, 2])
zs == [1, 2]   # → True
zs == [1, 3]   # → False

# concatenation / repetition
zs + [3, 4]    # → [1, 2, 3, 4]
zs * 3         # → [1, 2, 1, 2, 1, 2]

xs.clear()
len(xs)        # → 0
```

## How It Works

`SwapDict` / `SwapList` automatically offloads values whose pickled size
meets or exceeds `size_threshold` to a SQLite database. Any pickle-able
object (not just `bytes`) is eligible.

| Value | Storage |
|---|---|
| Pickle size < `size_threshold` | In-memory |
| Pickle size >= `size_threshold` | SQLite (transparent) |

Spilled values are retrieved, updated, and deleted using the same `dict`/`list`
interface — no special API calls needed.

## Caveats

- `size_threshold` is the pickle-size threshold in bytes; values >= this size
  are spilled.
- `size_threshold` cannot be changed after instantiation.
- Any pickle-able object type (not only `bytes`) can be spilled.
- Deleting the SQLite database will cause errors on previously spilled items.

## License

MIT
