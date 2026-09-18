# 数据结构设计：从操作契约倒推结构组合

## Problem Shape

- 题目给出一组长期调用的操作，并明确每个操作的复杂度目标。
- 单一基础结构无法同时满足查询、更新、顺序、淘汰或随机访问要求。

## Core Invariant

多个底层结构必须始终表示同一逻辑集合：每次写操作要原子地更新所有索引、链表、堆或数组位置；任何缓存顺序都准确反映淘汰策略。

## Why It Works

先列操作复杂度表，再为每项选择能力：哈希负责定位，链表负责 `O(1)` 顺序移动，数组负责随机访问，堆负责优先级，二分结构负责范围查询。组合后的同步不变量决定正确性。

## Compact Template

```python
class Structure:
    def __init__(self):
        self.by_key = {}
        self.order = SupportingStructure()

    def mutate(self, key, value):
        # 同一次操作内维护所有表示之间的一致性
        update_primary(key, value)
        update_secondary_index(key, value)
```

## Common Mistakes

- 只分析单个底层操作，没有给出整个公开操作的复杂度。
- 删除数组元素后忘记修复被交换元素在哈希中的下标。
- LRU 更新值却没有移动到最近使用端。
- 堆使用惰性删除，却没有跳过过期记录。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 普通算法题 | 对象会接收一系列在线操作 | 一次输入产生一次输出 |
| Hash Map | 单一索引已满足全部操作 | 还需要顺序、随机或优先级能力 |
| 系统设计 | 单进程内存结构与复杂度契约 | 分布式容量、容错与服务边界 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #380 Insert Delete GetRandom O(1) | 哈希与数组同步 |
| Transfer | #146 LRU Cache | 哈希与双向链表同步 |
| Advanced | #715 Range Module | 动态维护区间集合 |

## Teach-back Prompts

- 逐项列出公开操作的时间和空间目标。
- 哪些结构保存同一数据的不同索引？
- 一次删除或更新要维护哪些同步不变量？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 均摊 O(1) 结构组合 | 0/1 | #380 Insert Delete GetRandom O(1) (todo) |
| 缓存淘汰 | 0/1 | #146 LRU Cache (todo) |
| 时间索引 | 0/1 | #981 Time Based Key-Value Store (todo) |
| 队列与环形缓冲区 | 0/1 | #622 Design Circular Queue (todo) |
| 区间结构 | 0/1 | #715 Range Module (todo) |

<!-- sweep-map:end -->
