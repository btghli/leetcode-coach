<!-- leetcode-meta
{
  "id": 98,
  "slug": "validate-binary-search-tree",
  "title": "Validate Binary Search Tree",
  "difficulty": "Medium",
  "tags": [
    "tree",
    "depth-first-search",
    "binary-search-tree",
    "binary-tree"
  ],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-13",
  "next_review": "2026-08-20",
  "mistake_tags": [
    "explanation-gap"
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
    "leetcode": "https://leetcode.com/problems/validate-binary-search-tree/",
    "leetcode_cn": "https://leetcode.cn/problems/validate-binary-search-tree/"
  }
}
-->

# Validate Binary Search Tree

- Link: https://leetcode.com/problems/validate-binary-search-tree/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一棵二叉树。
- Output: 判断它是否满足严格 BST 性质。
- Constraints that matter: 右/左子树必须满足所有祖先约束，不只是直接父子关系；重复值不合法。

## Key Observations

- 合法 BST 的中序遍历序列严格递增。
- 只需保存中序遍历中上一个访问值 `prev`，无需保存完整序列。
- 空树是合法 BST。

## Approach

### Brute Force

- Idea:
- Complexity:
- Why it is not enough:

### Optimized

- Core invariant: 访问当前节点前，左子树已经验证完毕；`prev` 是中序遍历中上一个已访问节点值，已访问前缀严格递增。
- Data structure / state: 递归调用栈和跨递归共享的 `prev`。
- Steps:

```text
1. 中序递归左子树，失败则立即返回 False。
2. 要求当前值严格大于 prev，然后更新 prev。
3. 中序递归右子树；空节点返回 True。
```

## Complexity

- Time: O(n)。
- Space: O(h)，平衡树 O(log n)，退化树最坏 O(n)。
- Why: 每个节点访问一次；递归栈深度等于树高。

## Teach Back

- Key invariant: 已访问的中序前缀严格递增，`prev` 是其中最后一个值。
- Why this data structure / state works: BST 的中序遍历严格递增；每个新值大于紧邻前值即可保证大于此前全部值。
- Complexity and tradeoff: 时间 O(n)、空间 O(h)；相比范围法，中序法保存前一个访问值，范围法保存祖先传下来的合法开区间。
- Easiest edge case to miss: 重复值必须因 `node.val <= prev` 判为非法；空节点返回 True。
- When this pattern does NOT apply: 若要在访问节点时直接表达祖先约束，使用 `dfs(node, lower, upper)` 更自然；非 BST 的普通树没有中序严格递增性质。

## Mistakes

- Mistake tag: explanation-gap
- Symptom: 最初把共享状态描述成“记录所有值/当前最大值”。
- Root cause: 没有精确定义中序遍历状态。
- Fix: 将状态命名为 `prev`，定义为中序遍历上一个访问节点值。

## Pattern

- Pattern name: BST 中序有序性。
- Related pattern note: `knowledge/patterns/tree.md`。
- Similar problems: #230 Kth Smallest Element in a BST、#530 Minimum Absolute Difference in BST。
- Contrast: 中序法检查全局严格递增；范围法向下传递 `(lower, upper)`。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
