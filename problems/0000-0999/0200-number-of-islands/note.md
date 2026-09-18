<!-- leetcode-meta
{
  "id": 200,
  "slug": "number-of-islands",
  "title": "Number of Islands",
  "difficulty": "Medium",
  "tags": [],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-15",
  "next_review": "2026-08-18",
  "mistake_tags": [
    "tradeoff-gap"
  ],
  "stats": {
    "attempts": 1,
    "hint_level_reached": 0,
    "solve_minutes": null,
    "first_try_ac": null,
    "judge_failures": [],
    "recall_score": 3,
    "teach_back_done": true,
    "last_mode": "blind-solve"
  },
  "links": {
    "leetcode": "https://leetcode.com/problems/number-of-islands/",
    "leetcode_cn": "https://leetcode.cn/problems/number-of-islands/"
  }
}
-->

# Number of Islands

- Link: https://leetcode.com/problems/number-of-islands/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 由 `"1"` 和 `"0"` 组成的二维网格。
- Output: 只通过上下左右相连的陆地连通分量数量。
- Constraints that matter: 斜对角不算连通；解法会原地修改 `grid`。

## Key Observations

- Observation 1: 扫描到一个尚未访问的 `"1"` 时，就发现了一个新岛屿。
- Observation 2: 从该格开始的 BFS 可以一次标记这个岛屿的所有陆地。
- Brute force bottleneck: 如果不记录已访问格子，同一块陆地会被重复遍历和计数。

## Approach

### Brute Force

- Idea: 从每个陆地格子重复搜索相邻陆地，但不共享访问状态。
- Complexity: 可能对同一连通分量做大量重复工作。
- Why it is not enough: 无法保证每个格子只处理一次。

### Optimized

- Core invariant: `queue` 中保存当前岛屿中已经发现、但还等待展开的陆地格子。
- Data structure / state: `deque` 进行 BFS；入队前将 `"1"` 改为 `"0"` 作为 visited 标记。
- Steps:

```text
1. 遍历网格，找到未访问的陆地时将答案加一。
2. 立即标记起点并入队，再不断展开上下左右的未访问陆地。
3. BFS 结束时，当前岛屿已全部淹没，继续扫描下一个起点。
```

## Complexity

- Time: `O(mn)`
- Space: `O(mn)` worst case
- Why: 每个格子最多入队和出队一次；队列在最坏情况下可以保存 `O(mn)` 个格子。

## Teach Back

- Key invariant: 队列中的格子都属于当前岛屿，并且已被标记，不会再次入队。
- Why this data structure / state works: 入队时就淹没陆地，能防止同一格被多个邻居重复入队。
- Complexity and tradeoff: BFS 和 DFS 都能解决连通分量问题；本实现用队列代替递归栈，但会修改输入。
- Easiest edge case to miss: 斜对角相邻的两个陆地格子不连通，应计为两个岛屿。
- When this pattern does NOT apply: 普通 BFS 不能直接求不同边权的最短路；非负带权图通常使用 Dijkstra。

## Mistakes

- Mistake tag: `tradeoff-gap`
- Symptom: Teach-back 时一度将带权最短路的选择说成 DFS。
- Root cause: 没有区分“遍历全部节点”与“按路径总成本最小的顺序展开”。
- Fix: 无权/等权最短路用 BFS；非负带权最短路用 Dijkstra；DFS 不保证最短路。

## Pattern

- Pattern name: Graph DFS/BFS Traversal
- Related pattern note: `knowledge/patterns/graph.md`
- Similar problems: 695. Max Area of Island; 994. Rotting Oranges
- Contrast: 本题只求连通分量，BFS 和 DFS 都可用；求无权最短步数时更强调 BFS 的分层性质。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
