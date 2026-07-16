> [English (English)](README.en.md) · **日本語**

# swapcollection

辞書型やリストに格納された大容量のオブジェクトを自動的にSQLiteへ退避し、メモリ使用量を削減するライブラリです。通常の `dict` / `list` と同じ書き方で使用できます。

## クイックスタート

```bash
pip install swapcollection
```

### SwapDict

```python
from swapcollection import SwapDict

# pickle したサイズが size_threshold 以上の値を SQLite へ退避
d = SwapDict(size_threshold=100)

# 小さい値はメモリに保持
d["name"] = "alice"
d.data  # → {'name': 'alice'}

# 大きい値は透過的に SQLite へ退避
d["blob"] = b"x" * 200
d.data  # → {'name': 'alice', 'blob': 'swapdict_<uuid>'}  (メモリにはIDのみ)

# 取得は通常の dict と同じ
d["blob"]  # → b'xxxxxxxx...'

# 標準の dict メソッドがすべて使える
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

# repr() でも退避値が解決される
repr(d)  # → "{'blob': b'xxx...', 'a': 1, 'b': 2, 'c': 99}"

# クラスメソッド
SwapDict.fromkeys(["x", "y"], 0)
# → {'x': 0, 'y': 0}

d.clear()
len(d)             # → 0
```

### SwapList

```python
from swapcollection import SwapList

# 同じしきい値の仕組み
xs = SwapList(size_threshold=100)

xs.append(42)
xs.append(b"y" * 200)
xs[0]    # → 42
xs[1]    # → b'yyyyyy...'

xs.insert(1, "hello")
list(xs)  # → [42, 'hello', b'yyyyyy...']

xs.extend([1.5, b"z" * 200])
len(xs)   # → 5

# スライス取得でも退避値が解決される
xs[1:3]   # → ['hello', b'yyyyyy...']

# スライス代入（退避値を含む）
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

# sort（退避値を含んでも動作）
ys = SwapList(size_threshold=50)
ys.extend([b"c" * 20, b"a" * 20, b"b" * 20])
ys.sort()
list(ys)  # → [b'aaaa...', b'bbbb...', b'cccc...']

# 比較も透過的
zs = SwapList([1, 2])
zs == [1, 2]   # → True
zs == [1, 3]   # → False

# 連結 / 繰り返し
zs + [3, 4]    # → [1, 2, 3, 4]
zs * 3         # → [1, 2, 1, 2, 1, 2]

xs.clear()
len(xs)        # → 0
```

## 仕組み

`SwapDict` / `SwapList` は、格納された値を pickle したサイズが `size_threshold` 以上の場合に、値をSQLiteへ自動的に退避します。`bytes` に限らず、任意のpickle可能なオブジェクトが対象です。

| 値 | 保存先 |
|---|---|
| pickleサイズ < `size_threshold` | メモリ |
| pickleサイズ >= `size_threshold` | SQLite |

SQLiteへ退避された値も、通常の `dict` / `list` と同じ方法で取得、更新、削除できます。

## 注意事項

- `size_threshold` は、SQLiteへ退避する pickle サイズの閾値をバイト単位で指定します。
- サイズが `size_threshold` と等しい値もSQLiteへ退避されます。
- `size_threshold` はインスタンス作成後に変更できません。
- 値の種類（`bytes` 以外も含む）は pickle サイズでのみ判断されます。
- SQLiteデータベースを削除すると、退避済みの値を取得できなくなり、エラーが発生します。

## ライセンス

MIT
