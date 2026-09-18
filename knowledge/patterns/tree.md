# 树：明确递归函数对一棵子树的契约

## Problem Shape

- 输入具有根、父子关系且通常无环。
- 目标涉及子树高度/贡献、根到节点路径、层级、BST 顺序、公共祖先或遍历序列构造。

## Core Invariant

- 前序型：进入节点时参数准确描述从根到当前节点的状态。
- 后序型：递归返回值完整概括该子树供父节点使用的信息。
- BFS：一轮开始时队列恰好包含当前层全部节点。
- BST：中序序列严格递增，或每个节点受祖先传下来的合法区间约束。

## Why It Works

树的子树天然互不重叠，可以独立求解后在父节点组合。先写出 `dfs(node)` 的返回契约，再决定前序处理、后序聚合还是需要全局答案。

## Compact Template

```python
def dfs(node):
    if not node:
        return identity
    left = dfs(node.left)
    right = dfs(node.right)
    update_global(node, left, right)
    return summary_for_parent(node, left, right)
```

## Common Mistakes

- 返回给父节点的单边贡献与可跨左右子树的全局答案混淆。
- 路径列表回溯时忘记撤销，兄弟子树互相污染。
- BST 只比较直接父子，没有传递祖先上下界。
- 递归深度可能达到 `O(n)`，却误写成始终 `O(log n)`。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 图 | 根结构、唯一父关系 | 可能有环或任意邻接关系 |
| BFS | 问最浅、层序或同层关系 | 问子树聚合、路径或结构构造 |
| Tree DP | 每节点返回固定局部摘要 | 状态还包含选择、容量等额外维度 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #104 Maximum Depth | 最小后序返回契约 |
| Transfer | #102 Level Order Traversal | 层边界不变量 |
| Advanced | #236 Lowest Common Ancestor | 子树返回信息的组合 |

## Teach-back Prompts

- `dfs(node)` 返回值用一句话怎样定义？
- 哪些信息通过参数向下传，哪些通过返回值向上传？
- 最坏树高是多少，空间复杂度如何变化？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| DFS 与后序聚合 | complete | #104 Maximum Depth of Binary Tree (complete) |
| 路径状态 | complete | #437 Path Sum III (complete) |
| 层序 BFS | complete | #102 Binary Tree Level Order Traversal (complete) |
| BST 有序性 | complete | #98 Validate Binary Search Tree (complete) |
| 最近公共祖先 | complete | #236 Lowest Common Ancestor of a Binary Tree (complete) |
| 构造与序列化 | complete | #105 Construct Binary Tree from Preorder and Inorder Traversal (complete) |

<!-- sweep-map:end -->
