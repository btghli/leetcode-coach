<!-- leetcode-meta
{
  "id": 437,
  "slug": "path-sum-iii",
  "title": "Path Sum III",
  "difficulty": "Medium",
  "tags": [
    "tree",
    "depth-first-search",
    "binary-tree",
    "prefix-sum"
  ],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-13",
  "next_review": "2026-08-14",
  "mistake_tags": [
    "python-api-detail",
    "mutation-aliasing"
  ],
  "stats": {
    "attempts": 1,
    "hint_level_reached": 4,
    "solve_minutes": null,
    "first_try_ac": false,
    "judge_failures": [
      "RE"
    ],
    "recall_score": 3,
    "teach_back_done": true,
    "last_mode": "debug-drill"
  },
  "links": {
    "leetcode": "https://leetcode.com/problems/path-sum-iii/",
    "leetcode_cn": "https://leetcode.cn/problems/path-sum-iii/"
  }
}
-->

# Path Sum III

- Link: https://leetcode.com/problems/path-sum-iii/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一棵可能含负数的二叉树和目标和。
- Output: 向下连续、起点和终点可为任意节点且路径和等于目标的路径数量。
- Constraints that matter: 路径不必从根开始；负数使普通滑动窗口失效。

## Key Observations

- 根到当前节点的前缀和为 `currSum`；祖先前缀 `currSum-targetSum` 每出现一次，就对应一条合法路径。
- `count[prefix]` 只统计当前递归路径上的祖先前缀，不能包含兄弟子树。
- `count = {0: 1}` 表示根之前的空前缀，使从根开始的合法路径能被计数。

## Approach

### Brute Force

- Idea:
- Complexity:
- Why it is not enough:

### Optimized

- Core invariant: 处理当前节点时，`count` 准确保存根到当前节点父节点路径上各前缀和的出现次数。
- Data structure / state: 当前前缀和、前缀和频次表、递归栈。
- Steps:

```text
1. 把当前节点值加入 currSum，查询 count[currSum-targetSum]。
2. 再把 currSum 加入 count，递归左右子树。
3. 离开节点时将 count[currSum] 减一，恢复父节点状态。
```

## Complexity

- Time: O(n)。
- Space: O(h)，最坏退化树为 O(n)。
- Why: 每个节点只做常数次哈希操作；递归栈和当前路径上的不同前缀数量均不超过树高。

## Teach Back

- Key invariant: `count` 只包含当前根到父节点路径上的前缀和频次。
- Why this data structure / state works: `currSum-oldSum=targetSum` 将任意祖先后的向下路径转成两个前缀之差。
- Complexity and tradeoff: 时间 O(n)、辅助空间 O(h)，用哈希计数避免从每个节点重新向下枚举。
- Easiest edge case to miss: 初始化 `{0: 1}`；必须先查询再加入当前前缀，避免 target 为 0 时计算空路径。
- When this pattern does NOT apply: 如果必须返回具体路径，频次表不能恢复节点序列，需要维护当前路径并复制符合条件的片段。

## Mistakes

- Mistake tag: python-api-detail
- Symptom: 内层 `dfs` 执行 `res += ...` 时出现 `UnboundLocalError`。
- Root cause: Python 将发生赋值的 `res` 视为内层局部变量。
- Fix: 在 `dfs` 中声明 `nonlocal res`，或改为让递归返回计数。

- Mistake tag: mutation-aliasing
- Symptom: 最初没有撤销共享的前缀和频次，可能让左子树状态污染右子树。
- Root cause: 把局部整数 `currSum` 的恢复和共享字典 `count` 的恢复混淆。
- Fix: 离开节点前执行 `count[currSum] -= 1`；整数参数无需手动减回。

## Pattern

- Pattern name: 树的路径状态 + 前缀和计数 + 回溯。
- Related pattern note: `knowledge/patterns/tree.md`、`knowledge/patterns/prefix-sum.md`。
- Similar problems: #560 Subarray Sum Equals K、#113 Path Sum II。
- Contrast: #113 保存根到叶子的具体路径；#437 统计任意祖先到当前节点的路径数量。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
