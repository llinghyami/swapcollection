> **English** · [日本語 (Japanese)](README.md)

# spilldict

A `dict` subclass that automatically spills large `bytes` values to SQLite,
keeping memory usage low while maintaining the familiar `dict` interface.

## Quick Start

```bash
pip install spilldict
```

```python
from spilldict import SpillDict

# Spill bytes >= 1 KB to SQLite
data = SpillDict("cache.db", binary_size=1024)

data["small"] = b"hello"
data["large"] = b"x" * 100_000

# Access transparently — same as a normal dict
print(data["small"])
print(len(data["large"]))
```

## How It Works

`SpillDict` automatically offloads `bytes` values that meet or exceed
`binary_size` to a SQLite database.

| Value | Storage |
|---|---|
| `bytes` < `binary_size` | In-memory |
| `bytes` >= `binary_size` | SQLite (transparent) |
| Non-`bytes` values | In-memory |

Spilled values are retrieved, updated, and deleted using the same `dict`
interface — no special API calls needed.

## Caveats

- `binary_size` is the threshold in bytes; values >= this size are spilled.
- `binary_size` cannot be changed after instantiation.
- Non-`bytes` values are always kept in memory, regardless of size.
- Deleting the SQLite database will cause `KeyError` on previously spilled
  keys.

## License

MIT
