<!-- leetcode-meta
{
  "id": 104,
  "slug": "maximum-depth-of-binary-tree",
  "title": "Maximum Depth of Binary Tree",
  "difficulty": "Easy",
  "tags": [
    "tree",
    "depth-first-search",
    "breadth-first-search",
    "binary-tree"
  ],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-13",
  "next_review": "2026-08-20",
  "mistake_tags": [
    "complexity-explanation-gap"
  ],
  "stats": {
    "attempts": 1,
    "hint_level_reached": 2,
    "solve_minutes": null,
    "first_try_ac": true,
    "judge_failures": [],
    "recall_score": 4,
    "teach_back_done": true,
    "last_mode": "guided-solve"
  },
  "links": {
    "leetcode": "https://leetcode.com/problems/maximum-depth-of-binary-tree/",
    "leetcode_cn": "https://leetcode.cn/problems/maximum-depth-of-binary-tree/"
  }
}
-->

# Maximum Depth of Binary Tree

- Link: https://leetcode.com/problems/maximum-depth-of-binary-tree/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一棵二叉树的根节点。
- Output: 从根到最远叶子路径上的节点数；空树返回 0。
- Constraints that matter: 树可能退化成链表，递归栈最坏达到 O(n)。

## Key Observations

- 左右子树互不重叠，可以独立计算最大深度。
- `dfs(node)` 返回以 `node` 为根的子树最大深度。
- 父节点在取得左右子树结果后做后序聚合。

## Approach

### Brute Force

- Idea:
- Complexity:
- Why it is not enough:

### Optimized

- Core invariant: 每次 `dfs(node)` 返回时，它准确表示以 `node` 为根的整棵子树最大深度。
- Data structure / state: 递归调用栈；无需额外容器。
- Steps:

```text
1. 空节点返回 0。
2. 递归取得左右子树深度。
3. 返回 1 + max(left, right)，其中 1 表示当前节点。
```

## Complexity

- Time: O(n)。
- Space: O(h)，h 为树高；平衡树 O(log n)，退化树最坏 O(n)。
- Why: 每个节点访问一次；同时存在的递归帧数量等于当前根到节点路径长度。

## Teach Back

- Key invariant: `dfs(node)` 返回当前子树的最大深度。
- Why this data structure / state works: 左右子树独立求解，父节点用最大值加当前节点聚合。
- Complexity and tradeoff: 时间 O(n)，空间 O(h)，不能忽略递归调用栈。
- Easiest edge case to miss: `None` 返回 0，叶子节点因此返回 1；空树答案是 0。
- When this pattern does NOT apply: 求最浅层/最近目标时 BFS 可提前停止；依赖完整根到当前路径时，要向下携带路径状态并在回溯时撤销。

## Mistakes

- Mistake tag: complexity-explanation-gap
- Symptom: 最初把递归空间写成 O(1)。
- Root cause: 只计算显式容器，没有计入递归调用栈。
- Fix: 递归空间统一按树高 h 分析，并分别说明平衡树与退化树。

## Pattern

- Pattern name: 树的 DFS 与后序聚合。
- Related pattern note: `knowledge/patterns/tree.md`。
- Similar problems: #543 Diameter of Binary Tree、#110 Balanced Binary Tree。
- Contrast: 路径状态向下传递；后序摘要通过返回值向上传递。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
