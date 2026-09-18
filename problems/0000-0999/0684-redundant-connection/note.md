<!-- leetcode-meta
{
  "id": 684,
  "slug": "redundant-connection",
  "title": "Redundant Connection",
  "difficulty": "Medium",
  "tags": [],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-16",
  "next_review": "2026-08-17",
  "mistake_tags": [
    "python-api-detail",
    "transition-error",
    "complexity-explanation-gap"
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
    "last_mode": "guided-solve"
  },
  "links": {
    "leetcode": "https://leetcode.com/problems/redundant-connection/",
    "leetcode_cn": "https://leetcode.cn/problems/redundant-connection/"
  }
}
-->

# Redundant Connection

- Link: https://leetcode.com/problems/redundant-connection/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一棵无向树额外加入一条边后得到的边列表。
- Output: 删除后能让图恢复为树的冗余边；有多个候选时按输入顺序返回最后的候选。
- Constraints that matter: 节点编号从 `1` 开始，图中恰好多一条边并且只有一个环。

## Key Observations

- Observation 1: 按输入顺序加边时，如果 `u` 和 `v` 已经连通，再加 `[u, v]` 就会形成环。
- Observation 2: 并查集中 `find(u) == find(v)` 当且仅当两个节点已经连通。
- Brute force bottleneck: 每加一条边都用 DFS/BFS 重新检查连通性，会重复遍历已处理的图。

## Approach

### Brute Force

- Idea: 在加入 `[u, v]` 前，从 `u` 执行 DFS/BFS，检查是否已能到达 `v`。
- Complexity: 一般为 `O(E(V + E))`；本题 `V ≈ E ≈ n` 时可写成 `O(n^2)`。
- Why it is not enough: 每次连通性查询都从头遍历，没有复用之前的合并结果。

### Optimized

- Core invariant: 每个连通分量由唯一 root 代表，两节点 root 相同就表示已连通。
- Data structure / state: `parent` 存并查集父链，`size` 存 root 所在集合的节点数。
- Steps:

```text
1. find 沿 parent 找到 root，并用路径压缩让路径上的节点直接指向 root。
2. 对每条 [u, v] 比较两个 root；相同则立即返回该边。
3. root 不同时，将较小集合挂到较大集合下，并更新新 root 的 size。
```

## Complexity

- Time: `O(E · α(V))`；本题为 `O(n · α(n))`，接近 `O(n)`。
- Space: `O(V)`；本题为 `O(n)`。
- Why: 每条边执行常数次 `find/union`，路径压缩与按大小合并使均摊操作为 `O(α(V))`；只保存每个节点的 parent 和 size。

## Teach Back

- Key invariant: `find(x)` 返回 `x` 所属连通分量的 root；路径压缩后，查找路径上的节点会直接指向 root。
- Why this data structure / state works: 连接两个 root 等价于合并两个完整连通分量；按 size 将小集合挂到大集合上可避免父链过长。
- Complexity and tradeoff: 时间 `O(E · α(V))`，空间 `O(V)`；它高效回答连通性，但丢失了具体路径结构。
- Easiest edge case to miss: 当前实现使用 `0` 作未初始化哨兵，这只因题目节点编号从 `1` 开始才安全。
- When this pattern does NOT apply: Union-Find 只能说明两节点是否连通，没有保存实际路径或距离，因此不能直接求最短路。

## Mistakes

- Mistake tag: `python-api-detail`, `transition-error`, `complexity-explanation-gap`
- Symptom: `defaultdict(0)` 触发 `TypeError`；首个 AC 版本没有路径压缩和 size 更新，最坏仍可退化为 `O(n^2)`。
- Root cause: `defaultdict` 的 factory 不是 callable，并且并查集的两个优化只建了状态、没有完成状态更新。
- Fix: 使用 `defaultdict(int)` 和 `defaultdict(lambda: 1)`；`find` 回写 root，union 按 size 合并并更新 size。

## Pattern

- Pattern name: Disjoint Set Union (Union-Find)
- Related pattern note: `knowledge/patterns/graph.md`
- Similar problems: 547. Number of Provinces; 721. Accounts Merge
- Contrast: DFS/BFS 通过展开邻接节点可恢复路径或遍历顺序；Union-Find 专注于动态合并和连通性查询。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
