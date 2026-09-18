# 堆与优先队列：只维护下一批最有希望的候选

## Problem Shape

- 反复取得当前最小/最大元素，数据还在持续加入。
- 求 Top K、合并多个有序源、动态中位数或按优先级调度任务。
- 不需要维护全部元素的完整顺序。

## Core Invariant

- Top K 小根堆始终保存扫描前缀中最大的 K 个值，堆顶是其中最弱候选。
- K 路合并堆中每一路最多一个当前头部，堆顶是全局下一元素。
- 双堆把数据分成有序的低半区和高半区，大小差不超过 1。

## Why It Works

堆只维护“下一步需要比较”的边界候选，把完全排序的 `O(n log n)` 降为 `O(n log k)` 或让在线查询保持对数复杂度。

## Compact Template

```python
heap = []
for x in stream:
    heappush(heap, x)
    if len(heap) > k:
        heappop(heap)
# heap 是前缀中的 top k；heap[0] 是第 k 大
```

## Common Mistakes

- Python `heapq` 是小根堆，最大堆通常存负值。
- 把整个输入都放进堆，丢失 `O(k)` 空间优势。
- 元组优先级相同时比较到不可比较对象，需要加入唯一序号。
- K 路合并弹出后忘记推进其来源序列。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 排序 | 在线到达或只需边界候选 | 需要完整有序输出、多次任意位置访问 |
| Quickselect | 在线/重复查询 Top K | 静态数组只做一次第 K 小查询 |
| 单调队列 | 候选会按时间窗口过期 | 候选按数值优先级弹出 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #215 Kth Largest Element | 固定大小候选堆 |
| Transfer | #23 Merge k Sorted Lists | 每个有序源只暴露一个候选 |
| Advanced | #295 Find Median from Data Stream | 双堆平衡两个半区 |

## Teach-back Prompts

- 堆中保存全部数据还是候选边界？
- 堆顶在当前问题中代表什么？
- 为什么堆大小是 K、路数或活跃任务数，而不是 n？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| Top K | complete | #215 Kth Largest Element in an Array (complete) |
| 多路合并 | 0/1 | #23 Merge k Sorted Lists (todo) |
| 双堆与动态中位数 | 0/1 | #295 Find Median from Data Stream (todo) |
| 任务调度与重组 | 0/1 | #621 Task Scheduler (todo) |

<!-- sweep-map:end -->
