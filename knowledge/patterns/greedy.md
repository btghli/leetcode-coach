# 贪心：用可证明的局部选择压缩状态

## Problem Shape

- 目标是最优值或可行性，但只需维护一个边界、余额或当前最优代表。
- 候选经过排序后，可以证明某个选择支配其他选择。
- 常见信号：最少次数、最多可达、删除最少、按结束时间选择。

## Core Invariant

扫描前缀后，维护量代表所有可行历史中对未来最有利的状态；被丢弃的历史已由支配关系或交换论证证明不可能更优。

## Why It Works

贪心不是“每次选看起来最好的”，而是证明任意最优解都能交换成包含当前选择的最优解，或证明当前边界完整概括了所有历史可能性。

## Compact Template

```python
state = initial
for item in ordered_items:
    if can_improve_or_extend(state, item):
        state = update(state, item)
return extract_answer(state)
```

## Common Mistakes

- 只有直觉，没有交换或支配证明。
- 排序键选错：区间选择通常按结束时间，不是开始时间。
- 把未来所需的多个状态压成一个值，却无法证明其他状态被支配。
- 用一个样例验证局部选择，误当成普遍正确性。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 动态规划 | 历史状态可被单个最优边界支配 | 多个历史状态对不同未来各有优势 |
| 二分答案 | 直接扫描能更新最优边界 | 只能用单调 `check(x)` 判断答案 |
| 区间 | 一般局部选择 | 核心结构是端点与重叠关系 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #55 Jump Game | 最远可达边界概括全部历史 |
| Transfer | #134 Gas Station | 总量判定与失败起点整体淘汰 |
| Contrast | #416 Partition Equal Subset Sum | 多个容量状态不能压成一个贪心值 |

## Teach-back Prompts

- 当前状态支配了哪些被丢弃状态？
- 能否把任意最优解交换成包含当前选择的解？
- 构造一个局部最优会失败的相邻问题。

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 最远可达边界 | 0/1 | #55 Jump Game (todo) |
| 局部贡献与重置 | 0/1 | #134 Gas Station (todo) |

<!-- sweep-map:end -->
