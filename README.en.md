> **English** · [日本語 (Japanese)](README.md)

# swapcollection

A library that automatically offloads large objects stored in a
`dict`/`list` to SQLite, reducing memory usage. It can be used with
the same syntax as a regular `dict`/`list`.

## Quick Start

```bash
pip install swapcollection
```

```python
from swapcollection import SwapDict, SwapList

# Spill values >= 1 MB (pickle size) to SQLite
data = SwapDict(size_threshold=1024)

data["small"] = b"hello"
data["large"] = b"x" * 100_000

# Access transparently — same as a normal dict
print(data["small"])
print(len(data["large"]))
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
