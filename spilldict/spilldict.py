"""A dict subclass that automatically spills large binary values to SQLite.

SpillDict behaves like a normal ``dict``, but when a ``bytes`` value exceeds
a configurable threshold it is transparently spilled to a SQLite BLOB column
— only a lightweight key reference remains in memory.

    +----------------------------+--------------+
    | value                      | stored in    |
    +----------------------------+--------------+
    | bytes < threshold          | memory       |
    | bytes >= threshold         | SQLite BLOB  |
    | non-bytes (int, str, etc.) | memory       |
    +----------------------------+--------------+

Useful when you need the simplicity of a dict interface but deal with many
large binary objects (images, video chunks, file contents, etc.).

Example::

    d = SpillDict("cache.db", binary_size=1024)
    d["small"] = b"hello"          # stays in memory
    d["big"]   = b"x" * 100_000    # spilled to SQLite
    print(d["big"])                 # transparently retrieved
"""

from sqlite_utils import Database
from sqlite_utils.db import NotFoundError
import uuid
import os


class SpillDict(dict):
    """dict subclass with automatic on-disk spillover for large binary values.

    Parameters
    ----------
    path : str
        Path to the SQLite database file used for spill storage.
        Defaults to ``"spilldict_cache.db"`` in the current directory.
    binary_size : int
        Minimum size (in bytes) at which a ``bytes`` value is spilled to
        SQLite instead of being kept in memory.  Must be >= 0.
        Defaults to 10240 (10 KB).

    Raises
    ------
    ValueError
        If *binary_size* is negative.
    """

    PREFIX = "spilldict_"

    def __init__(
        self,
        path: str = "spilldict_cache.db",
        binary_size: int = 10240
    ):
        super().__init__()

        if binary_size < 0:
            raise ValueError("binary_size must be >= 0")

        self.db = Database(path)
        self.binary_size = binary_size
        self.table = self.db["items"]

        if not self.table.exists():
            self.table.create(
                {
                    "id": str,
                    "value": bytes,
                },
                pk="id",
            )

    def __setitem__(self, key, value):
        """Store *value* at *key*, spilling large ``bytes`` to SQLite."""
        if type(value) is bytes and len(value) >= self.binary_size:
            blob_id = f"{self.PREFIX}{uuid.uuid4().hex}"

            self.table.insert({
                "id": blob_id,
                "value": value,
            })

            value = blob_id

        super().__setitem__(key, value)

    def __getitem__(self, key):
        """Retrieve the value at *key*, rehydrating from SQLite if needed."""
        value = super().__getitem__(key)

        if type(value) is str and value.startswith(self.PREFIX):
            try:
                return self.table.get(value)["value"]
            except NotFoundError:
                raise KeyError(
                    f"Spilled blob not found in SQLite: {value}"
                ) from None

        return value

if __name__ == "__main__":

    tmp = SpillDict(binary_size=1)

    tmp["a"] = b"123sdasda"
    tmp["b"] = 123
    tmp["c"] = "hello"

    print(tmp)       # 内部的にはIDが保存されている
    print(tmp["a"])  # b'123sdasda'
    print(tmp["b"])  # 123
    print(tmp["c"])  # hello