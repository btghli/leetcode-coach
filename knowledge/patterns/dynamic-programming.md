# 动态规划：为重叠子问题定义可复用状态

## Problem Shape

- 求最优值、可行性或方案数，直接递归会反复求解相同子问题。
- 当前决策只依赖一个可压缩的历史摘要，而非完整路径。
- 常见维度：位置、容量、前缀长度、持有状态、左右边界、位掩码。

## Core Invariant

`dp[state]` 必须是一句无歧义的话；计算它时依赖的所有前驱状态已经正确。遍历顺序来自依赖方向，而不是背模板。

## Why It Works

最优子结构保证全局答案可由子问题答案组合；状态覆盖了未来决策所需的全部信息；记忆化或填表让每个状态只计算一次。

## Compact Template

```python
@cache
def dp(state):
    if base(state):
        return base_value(state)
    return combine(dp(prev) + cost for prev in predecessors(state))

# 自底向上：先写状态定义和依赖，再决定循环方向
```

## Common Mistakes

- 先写数组再猜状态，导致转移缺信息。
- 0/1 背包正序更新容量，使同一物品被重复使用。
- 初始化把“不可达”与值 0 混为一谈。
- 空间压缩后仍按旧依赖方向遍历，覆盖尚未使用的状态。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 回溯 | 只求值/计数，子问题重叠 | 必须输出全部具体构造 |
| 贪心 | 当前选择会影响未来且无交换证明 | 可证明局部选择不损失全局最优 |
| 二分答案 | 可行性关于答案单调 | 状态沿结构递推、答案不具单调判定 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #70 Climbing Stairs | 一维递推与空间压缩 |
| Transfer | #416 Partition Equal Subset Sum | 0/1 背包与遍历方向 |
| Contrast | #55 Jump Game | 可用贪心边界压缩状态 |

## Teach-back Prompts

- 用完整句子定义状态，指出每个维度为什么必要。
- 转移依赖谁，为什么当前遍历顺序正确？
- 空间压缩会不会覆盖仍需读取的旧状态？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 一维状态 | 0/1 | #70 Climbing Stairs (todo) |
| 背包 | 0/1 | #416 Partition Equal Subset Sum (todo) |
| 网格 DP | 0/1 | #62 Unique Paths (todo) |
| 双序列 DP | 0/1 | #1143 Longest Common Subsequence (todo) |
| 子序列 | 0/1 | #300 Longest Increasing Subsequence (todo) |
| 状态机 DP | 0/1 | #309 Best Time to Buy and Sell Stock with Cooldown (todo) |
| 区间 DP | 0/1 | #516 Longest Palindromic Subsequence (todo) |

<!-- sweep-map:end -->
