<!-- leetcode-meta
{
  "id": 102,
  "slug": "binary-tree-level-order-traversal",
  "title": "Binary Tree Level Order Traversal",
  "difficulty": "Medium",
  "tags": [
    "tree",
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
    "leetcode": "https://leetcode.com/problems/binary-tree-level-order-traversal/",
    "leetcode_cn": "https://leetcode.cn/problems/binary-tree-level-order-traversal/"
  }
}
-->

# Binary Tree Level Order Traversal

- Link: https://leetcode.com/problems/binary-tree-level-order-traversal/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一棵二叉树的根节点。
- Output: 按从上到下、每层从左到右返回节点值。
- Constraints that matter: 空树返回空列表；需要保持清晰的层边界。

## Key Observations

- 每轮开始时，队列中恰好是当前层全部节点。
- 必须在处理本层前固定 `level_size`，因为遍历时下一层孩子会继续入队。
- `deque.popleft()` 为 O(1)；列表 `pop(0)` 虽然逻辑正确，但单次为 O(n)。

## Approach

### Brute Force

- Idea:
- Complexity:
- Why it is not enough:

### Optimized

- Core invariant: 每轮 `while` 开始时，队列恰好包含当前层全部节点。
- Data structure / state: `deque`、固定的当前层大小和当前层结果列表。
- Steps:

```text
1. 空树直接返回 []，否则根节点入队。
2. 固定当前 queue 长度，只弹出这批节点并收集值。
3. 把孩子加入队尾；本轮结束后队列恰好是下一层。
```

## Complexity

- Time: O(n)。
- Space: O(w)，w 为最大层宽，最坏 O(n)。
- Why: 每个节点入队、出队各一次，队列峰值由最大层宽决定。

## Teach Back

- Key invariant: 每轮开始时 queue 中保存当前层节点。
- Why this data structure / state works: 固定 `level_size` 后，本轮新增的孩子只会留给下一轮。
- Complexity and tradeoff: 时间 O(n)、空间 O(w)；用 deque 避免列表头删的移动成本。
- Easiest edge case to miss: `root is None` 时返回 `[]`。
- When this pattern does NOT apply: 子树摘要聚合更适合 DFS；最小深度、最近目标、层宽和同层信息更适合 BFS，并可在首次找到最近目标时提前结束。

## Mistakes

- Mistake tag: complexity-explanation-gap
- Symptom: 最初认为列表 `pop(0)` 与 `deque.popleft()` 性能相同，并把空间写成叶子数。
- Root cause: 忽略列表头删需要整体左移，也没有用最大层宽定义队列峰值。
- Fix: BFS 队列使用 deque；空间统一写 O(w)，最坏 O(n)。

## Pattern

- Pattern name: 树的层序 BFS。
- Related pattern note: `knowledge/patterns/tree.md`。
- Similar problems: #111 Minimum Depth of Binary Tree、#199 Binary Tree Right Side View。
- Contrast: BFS 维护层级前沿；后序 DFS 返回子树摘要。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
