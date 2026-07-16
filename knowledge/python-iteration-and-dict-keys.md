# Python 遍历与 dict key 速查

来源:2026-07-16 复习 49. Group Anagrams 时踩坑总结。
关联错误标签:`python-api-detail`

## 遍历速查

| 你要什么 | 写法 |
|---|---|
| list 的值 | `for x in lst` |
| list 的下标+值 | `for i, x in enumerate(lst)` |
| dict 的 key | `for k in d` |
| dict 的 value | `for v in d.values()` |
| dict 的键值对 | `for k, v in d.items()` |
| 两个列表并行 | `for a, b in zip(l1, l2)` |
| 倒序 | `for x in reversed(lst)` |
| 下标 + 键值对 | `for i, (k, v) in enumerate(d.items())` |

核心记忆点:

- **`for k, v in d` 是错的**,直接遍历 dict 只给 key;想解包必须 `.items()`。
  (阴险之处:若 key 恰好是二元 tuple,`for k, v in d` 不报错但语义全错。)
- 需要下标用 `enumerate`,`range(len(...))` 是最后手段。

## dict key 的哈希规则

**做 dict 的 key / 进 set 的元素,必须不可变(可哈希)。**

| 想用的类型 | 能否做 key | 替代方案 |
|---|---|---|
| `list` | ❌ `TypeError: unhashable type` | `tuple(lst)` |
| `dict` / `Counter` | ❌ 同上 | `frozenset(d.items())` 或 `tuple(sorted(d.items()))` |
| `set` | ❌ | `frozenset(s)` |
| `tuple` / `str` / 数字 | ✅ | — |

原因:哈希表按 key 的哈希值定位桶;可变对象改动后哈希值变化,条目会"丢失",所以 Python 禁止。

## defaultdict 两个必记点

```python
from collections import defaultdict
groups = defaultdict(list)   # ✅ 必须传工厂函数
groups = defaultdict()       # ❌ 不传等于普通 dict,照样 KeyError
```

- 工厂是**函数**(`list`、`int`、`set`),缺 key 时自动调用生成默认值。
- 返回结果时通常 `list(groups.values())`。

## 关联题目

- 49. Group Anagrams:计数 list → `tuple` 做 key;字符集任意时 `frozenset(Counter(s).items())`。
