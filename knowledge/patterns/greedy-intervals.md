# 区间与扫描线：先统一边界语义，再按端点排序

## Problem Shape

- 输入是一组 `[start, end]`，目标是合并、插入、求交、选择最多互不重叠区间或统计同时活跃数量。
- 端点事件比区间内部细节更重要；排序后可线性处理。

## Core Invariant

- 合并时，结果列表最后一个区间是已扫描前缀的唯一未封口区间。
- 双列表求交时，较早结束的区间不可能再与对方后续区间相交，可安全前进。
- 扫描线中，活跃计数等于当前位置之前已开始但尚未结束的事件数。

## Why It Works

排序建立端点单调性，使一个区间一旦结束就无需回看。闭区间、半开区间以及同坐标的事件处理顺序必须先定义，否则“相接是否重叠”没有统一答案。

## Compact Template

```python
intervals.sort(key=lambda x: x[0])
merged = []
for start, end in intervals:
    if not merged or start > merged[-1][1]:
        merged.append([start, end])
    else:
        merged[-1][1] = max(merged[-1][1], end)
```

## Common Mistakes

- 忘记空输入。
- 只判断包含关系，没有处理部分重叠。
- 对相同坐标的 start/end 事件排序错误。
- 区间调度按开始时间而非结束时间选择，却没有证明。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 差分数组 | 坐标范围巨大或需保留具体区间 | 坐标范围小、只需累计覆盖数 |
| 堆 | 只做离线合并/选择 | 在线维护多个仍活跃的结束时间 |
| 贪心 | 题目核心是端点与重叠 | 一般状态选择，不一定有区间输入 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #56 Merge Intervals | 排序后维护未封口区间 |
| Transfer | #986 Interval List Intersections | 双序列端点淘汰 |
| Contrast | #1109 Corporate Flight Bookings | 有界坐标批量更新更适合差分 |

## Teach-back Prompts

- 输入区间是闭区间还是半开区间？
- 为什么较早结束的一侧可以永久前进？
- 同一坐标的开始和结束事件谁先处理？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 区间合并 | 1/2 | #56 Merge Intervals (complete); #57 Insert Interval (todo) |
| 区间交集 | 0/1 | #986 Interval List Intersections (todo) |
| 区间调度 | 0/1 | #435 Non-overlapping Intervals (todo) |
| 重叠计数与会议室 | 0/1 | #253 Meeting Rooms II (todo) |

<!-- sweep-map:end -->
