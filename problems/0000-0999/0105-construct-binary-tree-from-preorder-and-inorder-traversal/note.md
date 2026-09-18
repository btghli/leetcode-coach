<!-- leetcode-meta
{
  "id": 105,
  "slug": "construct-binary-tree-from-preorder-and-inorder-traversal",
  "title": "Construct Binary Tree from Preorder and Inorder Traversal",
  "difficulty": "Medium",
  "tags": [
    "array",
    "hash-table",
    "divide-and-conquer",
    "tree",
    "binary-tree"
  ],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-13",
  "next_review": "2026-08-16",
  "mistake_tags": [
    "complexity-explanation-gap"
  ],
  "stats": {
    "attempts": 1,
    "hint_level_reached": 3,
    "solve_minutes": null,
    "first_try_ac": true,
    "judge_failures": [],
    "recall_score": 4,
    "teach_back_done": true,
    "last_mode": "guided-solve"
  },
  "links": {
    "leetcode": "https://leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal/",
    "leetcode_cn": "https://leetcode.cn/problems/construct-binary-tree-from-preorder-and-inorder-traversal/"
  }
}
-->

# Construct Binary Tree from Preorder and Inorder Traversal

- Link: https://leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一棵二叉树的前序遍历 `preorder` 和中序遍历 `inorder`。
- Output: 根据两个遍历序列重建的二叉树根节点。
- Constraints that matter: 节点值互不相同，两个序列描述同一棵树。

## Key Observations

- Observation 1: 前序遍历的第一个值是当前子树的根。
- Observation 2: 根在中序遍历中将序列分成左、右子树；左半部分的长度同时决定前序序列的切分点。
- Brute force bottleneck: 每层递归都使用 `inorder.index` 线性查找根，并创建新切片。

## Approach

### Brute Force

- Idea: 取 `preorder[0]` 作为根，在 `inorder` 中搜索根的位置，切出左右子树序列后递归。这是本次 Judge AC 的实际解法。
- Complexity: 平衡树时间 `O(n log n)`，极端斜树时 `O(n^2)`；切片的额外空间最坏也是 `O(n^2)`。
- Why it is not enough: 重复查找和拷贝元素，无法保证线性复杂度。

### Optimized

- Core invariant: 递归参数中的前序区间与中序区间始终表示同一棵子树。
- Data structure / state: 使用 `value -> inorder index` 哈希表，并用左闭右开的索引区间代替切片。
- Steps:

```text
1. 空区间返回 None，否则取前序区间的第一个值作根。
2. 用哈希表找到根在中序遍历中的位置，计算左子树大小。
3. 按左子树大小切分索引区间，递归构建左右子树。
```

## Complexity

- Time: `O(n)`
- Space: `O(n) + O(h)`
- Why: 每个节点只创建一次，哈希表查找均摊 `O(1)`；哈希表占 `O(n)`，递归栈占 `O(h)`。

## Teach Back

- Key invariant: 递归函数返回当前两个遍历区间组成的子树根节点。
- Why this data structure / state works: 前序首元素确定根，中序中根的位置确定左子树大小，因此两个序列都能被唯一分割。
- Complexity and tradeoff: AC 版本更直观，但切片与 `index` 使它最坏达到 `O(n^2)`；哈希表加索引区间可优化为 `O(n)`。
- Easiest edge case to miss: 空序列应返回 `None`，以及只有单侧子树时的区间边界。
- When this pattern does NOT apply: 如果节点值可重复，仅靠值无法唯一确定根在中序序列中对应的那一次出现。

## Mistakes

- Mistake tag: `complexity-explanation-gap`
- Symptom: 将使用 `list.index` 和切片的递归解法说成时间 `O(n)`、空间 `O(h)`。
- Root cause: 只统计了节点数和递归深度，漏掉每层的线性搜索与切片拷贝。
- Fix: 复杂度分析时单独列出每次调用做的非递归工作；需要线性总复杂度时使用哈希表和索引区间。

## Pattern

- Pattern name: Tree Construction / Divide and Conquer
- Related pattern note: `knowledge/patterns/tree.md`
- Similar problems: 106. Construct Binary Tree from Inorder and Postorder Traversal
- Contrast: 与普通 DFS 汇总不同，本题是先由遍历序列确定根与子树边界，再分治构造结果树。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
