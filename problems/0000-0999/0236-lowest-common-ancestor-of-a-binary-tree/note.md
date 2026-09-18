<!-- leetcode-meta
{
  "id": 236,
  "slug": "lowest-common-ancestor-of-a-binary-tree",
  "title": "Lowest Common Ancestor of a Binary Tree",
  "difficulty": "Medium",
  "tags": [
    "tree",
    "depth-first-search",
    "binary-tree"
  ],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-13",
  "next_review": "2026-08-20",
  "mistake_tags": [
    "constraint-misread"
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
    "leetcode": "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/",
    "leetcode_cn": "https://leetcode.cn/problems/lowest-common-ancestor-of-a-binary-tree/"
  }
}
-->

# Lowest Common Ancestor of a Binary Tree

- Link: https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一棵普通二叉树，以及树中两个不同节点 `p`、`q`。
- Output: 两者最低的公共祖先；节点可以是自己的祖先。
- Constraints that matter: `p`、`q` 都保证存在于树中；不能利用 BST 大小关系。

## Key Observations

- 子树需要向父节点报告找到的单个目标，或已经确定的 LCA。
- 左右子树都返回非空时，当前节点是两条目标路径首次汇合的位置。
- 只有一侧非空时，原样向上传；它可能是单个目标，也可能是子树内已经确定的 LCA。

## Approach

### Brute Force

- Idea:
- Complexity:
- Why it is not enough:

### Optimized

- Core invariant: `dfs(node)` 返回当前子树中的唯一目标或已确定的 LCA；若一个目标都没有则返回 `None`。
- Data structure / state: 递归返回的节点引用。
- Steps:

```text
1. 空节点返回 None；当前节点是 p/q 时返回当前节点。
2. 分别递归左右子树。
3. 两侧非空返回当前节点；否则返回唯一非空侧。
```

## Complexity

- Time: O(n)。
- Space: O(h)，平衡树 O(log n)，退化树最坏 O(n)。
- Why: 最坏访问每个节点一次；递归栈深度等于树高。

## Teach Back

- Key invariant: 非空返回值既可能是找到的单个目标，也可能是当前子树已经确定的 LCA。
- Why this data structure / state works: 两侧同时非空说明目标分居两侧，当前节点为最低汇合点；只有一侧非空时当前节点没有形成更高的新汇合，应原样向上传。
- Complexity and tradeoff: 时间 O(n)、空间 O(h)。
- Easiest edge case to miss: `p` 是 `q` 的祖先时，遇到 `p` 直接返回即可；比较的是节点身份而非仅比较值。
- When this pattern does NOT apply: 简洁写法依赖两个目标都存在；若目标可能缺失，需额外返回 `found_count`，只有计数为 2 才接受候选 LCA。

## Mistakes

- Mistake tag: constraint-misread
- Symptom: 最初认为目标缺失时算法会返回 None。
- Root cause: 没有识别简洁返回契约依赖题目保证两个目标都存在。
- Fix: 若缺少存在性保证，让递归同时返回候选节点与找到的目标数量。

## Pattern

- Pattern name: 最近公共祖先与子树信号聚合。
- Related pattern note: `knowledge/patterns/tree.md`。
- Similar problems: #235 Lowest Common Ancestor of a BST、#1644 Lowest Common Ancestor of a Binary Tree II。
- Contrast: #235 可利用 BST 有序性；本题必须搜索普通二叉树结构。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
