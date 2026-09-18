# 回溯：显式遍历选择树

## Problem Shape

- 要列出所有组合、排列、切割方案或满足约束的构造。
- 输入规模较小，答案数量本身可能指数级。
- 每一步都有候选选择，并且选择会影响后续合法性。

## Core Invariant

进入 `dfs` 时，`path` 恰好描述当前根到节点的选择；候选集合只包含仍可合法扩展的动作。递归返回前撤销本层修改，使兄弟分支看到相同父状态。

## Why It Works

搜索树的每个叶子对应一个候选解；候选起点、`used` 或约束集合保证不重复也不漏。剪枝只能删除已证明不可能产生合法解或更优解的整棵子树。

## Compact Template

```python
def dfs(start):
    if complete(path):
        ans.append(path.copy())
        return
    for i in range(start, len(candidates)):
        if invalid(i) or duplicate_on_same_level(i):
            continue
        choose(i)
        dfs(next_start(i))
        undo(i)
```

## Common Mistakes

- 保存 `path` 本身而不是 `path.copy()`，结果被后续撤销污染。
- 组合与排列混用：组合用递增 `start`，排列通常用 `used`。
- 去重层级错误：同层跳重与同一路径禁用不是一回事。
- 在验证约束前递归，造成无意义的指数爆炸。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 动态规划 | 必须枚举或构造所有方案 | 只求计数/最优值且状态大量重叠 |
| 图 DFS | 节点是显式输入关系 | 节点由选择过程隐式生成 |
| 贪心 | 无法安全丢弃其他选择 | 有交换论证可保留单一路径 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #78 Subsets | 选/不选与候选起点 |
| Transfer | #131 Palindrome Partitioning | 切割位置生成搜索树 |
| Advanced | #79 Word Search | 原地标记、撤销与邻接约束 |

## Teach-back Prompts

- 当前 `path`、候选集合和终止条件分别是什么？
- 去重发生在同层还是同一路径？
- 哪条证明允许当前剪枝？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 子集与选择 | complete | #78 Subsets (complete) |
| 排列与使用标记 | complete | #46 Permutations (complete) |
| 组合与候选起点 | complete | #39 Combination Sum (complete) |
| 切割与分段 | complete | #131 Palindrome Partitioning (complete) |
| 棋盘搜索与约束传播 | complete | #79 Word Search (complete) |

<!-- sweep-map:end -->
