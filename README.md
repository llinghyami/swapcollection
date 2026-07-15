> [English (English)](README.en.md) · **日本語**

# spilldict

辞書型に格納された大容量の `bytes` を自動的にSQLiteへ退避し、メモリ使用量を削減するライブラリです。通常の `dict` と同じ書き方で使用できます。

## クイックスタート

```bash
pip install spilldict
```

```python
from spilldict import SpillDict

# 1 KB以上のbytesをSQLiteへ退避
data = SpillDict("cache.db", binary_size=1024)

data["small"] = b"hello"
data["large"] = b"x" * 100_000

# 通常のdictと同じように取得
print(data["small"])
print(len(data["large"]))
```

## 仕組み

`SpillDict` は、格納された値が `bytes` であり、そのサイズが `binary_size` 以上の場合に、値をSQLiteへ自動的に退避します。

| 値 | 保存先 |
|---|---|
| `binary_size` 未満の `bytes` | メモリ |
| `binary_size` 以上の `bytes` | SQLite |
| `bytes` 以外の値 | メモリ |

SQLiteへ退避された値も、通常の `dict` と同じ方法で取得、更新、削除できます。

## 注意事項

- `binary_size` は、SQLiteへ退避する `bytes` のサイズをバイト単位で指定します。
- サイズが `binary_size` と等しい `bytes` もSQLiteへ退避されます。
- `binary_size` はインスタンス作成後に変更できません。
- `bytes` 以外の値は、サイズにかかわらずメモリに保存されます。
- SQLiteデータベースを削除すると、退避済みの値を取得できなくなり、`KeyError` が発生します。

## ライセンス

MIT
