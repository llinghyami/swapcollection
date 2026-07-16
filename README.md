> [English (English)](README.en.md) · **日本語**

# swapcollection

辞書型やリストに格納された大容量のオブジェクトを自動的にSQLiteへ退避し、メモリ使用量を削減するライブラリです。通常の `dict` / `list` と同じ書き方で使用できます。

## クイックスタート

```bash
pip install swapcollection
```

```python
from swapcollection import SwapDict, SwapList

# 1 MB以上の値をSQLiteへ退避
data = SwapDict(size_threshold=1024)

data["small"] = b"hello"
data["large"] = b"x" * 100_000

# 通常のdictと同じように取得
print(data["small"])
print(len(data["large"]))
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
