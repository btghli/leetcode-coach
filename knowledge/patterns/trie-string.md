# Trie 与字符串匹配：复用公共前缀或匹配状态

## Problem Shape

- 大量单词需要前缀查询、逐字符搜索、自动补全或与网格 DFS 联动。
- 在长文本中重复查找模式串，希望避免每个起点重新比较。

## Core Invariant

- Trie 节点代表从根到该节点的唯一前缀；沿字符边前进等价于扩展匹配前缀。
- KMP 的匹配长度 `j` 表示当前文本后缀与模式前缀相等的最大长度。
- Rolling Hash 的窗口哈希通过移出、移入字符增量更新；哈希相等仍可能需要防碰撞验证。

## Why It Works

Trie 在共享前缀间复用遍历；KMP 用前缀函数复用已匹配信息，失配时不让文本指针回退；滚动哈希让每个等长窗口的指纹以 `O(1)` 更新。

## Compact Template

```python
node = root
for ch in word:
    node = node.children.setdefault(ch, Node())
node.is_word = True

# 搜索时：缺边即失败；走完后按题意检查 is_word 或只检查前缀存在
```

## Common Mistakes

- 混淆“前缀存在”和“完整单词存在”。
- Trie + DFS 找到单词后不去重，重复输出。
- KMP 的前缀函数含义不清，失配跳转下标差一位。
- Rolling Hash 忽略碰撞或负模归一化。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| Hash Set | 单次完整字符串查询 | 大量前缀查询或字符级剪枝 |
| KMP | 单模式精确线性匹配 | 多单词共享前缀用 Trie |
| 回溯 | Trie 提供前缀剪枝 | 只枚举单个单词路径可直接 DFS |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #208 Implement Trie | 前缀节点语义与终止标记 |
| Transfer | #212 Word Search II | Trie 剪掉不可能的网格路径 |
| Contrast | #49 Group Anagrams | 只需完整键分组，哈希更直接 |

## Teach-back Prompts

- Trie 节点究竟代表字符还是前缀？
- KMP 失配时复用了哪一段已知匹配？
- 何时哈希碰撞会影响正确性？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 前缀树 | 0/1 | #208 Implement Trie (Prefix Tree) (todo) |
| Trie 与通配符 | 0/1 | #211 Design Add and Search Words Data Structure (todo) |
| Trie 与 DFS | 0/1 | #212 Word Search II (todo) |
| 精确字符串匹配 | 0/1 | #28 Find the Index of the First Occurrence in a String (todo) |
| 滚动哈希 | 0/1 | #187 Repeated DNA Sequences (todo) |

<!-- sweep-map:end -->
