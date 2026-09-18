# 数组与哈希：把值映射为可维护的状态

## Problem Shape

- 需要按值快速定位次数、最早/最后位置、所属分组或是否出现。
- 数值范围可映射到下标时，可能用原地归位或符号标记换取 `O(1)` 额外空间。
- 输出依赖“除自身外的聚合”时，考虑前后缀；只关心相对顺序时，先排序可能暴露结构。

## Core Invariant

- 哈希表保存扫描前缀中回答未来查询所需的最小状态，而不是复制全部历史。
- 原地归位中，索引 `i` 对应唯一目标值；每次交换至少让一个值进入最终位置。
- 前后缀聚合在处理 `i` 时，左右累积量都严格不包含 `nums[i]`。

## Why It Works

哈希将“回头查找”降为均摊 `O(1)`；下标归位利用有限值域让每个元素只被搬动常数次；排序用 `O(n log n)` 的预处理换来相邻性和单调性。选择前先说明是否必须保留原始下标与顺序。

## Compact Template

```python
seen = {}
for i, x in enumerate(nums):
    if need(x) in seen:
        return seen[need(x)], i
    seen[x] = i

# 值域为 1..n 的下标归位
i = 0
while i < len(nums):
    j = nums[i] - 1
    if 0 <= j < len(nums) and nums[i] != nums[j]:
        nums[i], nums[j] = nums[j], nums[i]
    else:
        i += 1
```

## Common Mistakes

- Two Sum 先写入再查询会让同一元素和自己配对。
- 把哈希空间笼统写成 `O(n)`；更精确是 `O(k)`，`k` 为不同状态数。
- 原地标记没有先验证值域，导致负下标或越界。
- 为了用双指针而排序，却破坏题目要求返回的原始下标。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 双指针 | 无序且需要原始下标/频次 | 已排序或允许排序，目标关系单调 |
| 前缀和 | 查询单个值或分组状态 | 查询连续区间的累计量 |
| 堆 | 只需记录出现次数 | 需要持续维护前 K 个候选 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #1 Two Sum | 补数查询与写入顺序 |
| Transfer | #41 First Missing Positive | 值到下标的原地映射 |
| Contrast | #167 Two Sum II | 已排序后双指针更省空间 |

## Teach-back Prompts

- 哈希表在扫描到 `i` 前准确保存什么？
- 为什么 cyclic placement 不是比较排序，却仍为 `O(n)`？
- 哪些输出要求会禁止先排序？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 计数与索引 | complete | #1 Two Sum (complete); #49 Group Anagrams (complete) |
| 集合去重与连续性 | complete | #128 Longest Consecutive Sequence (complete) |
| 下标归位与原地标记 | 0/2 | #41 First Missing Positive (todo); #448 Find All Numbers Disappeared in an Array (todo) |
| 前后缀聚合 | 0/1 | #238 Product of Array Except Self (todo) |
| 排序、分区与选择 | 0/1 | #75 Sort Colors (todo) |

<!-- sweep-map:end -->
