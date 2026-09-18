<!-- leetcode-meta
{
  "id": 994,
  "slug": "rotting-oranges",
  "title": "Rotting Oranges",
  "difficulty": "Medium",
  "tags": [],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-16",
  "next_review": "2026-08-17",
  "mistake_tags": [
    "duplicate-handling",
    "complexity-explanation-gap"
  ],
  "stats": {
    "attempts": 1,
    "hint_level_reached": 4,
    "solve_minutes": null,
    "first_try_ac": true,
    "judge_failures": [],
    "recall_score": 4,
    "teach_back_done": true,
    "last_mode": "guided-solve"
  },
  "links": {
    "leetcode": "https://leetcode.com/problems/rotting-oranges/",
    "leetcode_cn": "https://leetcode.cn/problems/rotting-oranges/"
  }
}
-->

# Rotting Oranges

- Link: https://leetcode.com/problems/rotting-oranges/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 一个网格，`0` 是空格、`1` 是新鲜橘子、`2` 是腐烂橘子。
- Output: 所有新鲜橘子腐烂的最少分钟数；无法全部腐烂时返回 `-1`。
- Constraints that matter: 每分钟所有腐烂橘子同时向上下左右传播。

## Key Observations

- Observation 1: 所有初始腐烂橘子都是第 `0` 分钟的起点，必须一起入队。
- Observation 2: BFS 的每一层对应一分钟；`freshCnt` 可判断传播是否完成。
- Brute force bottleneck: 从每个腐烂橘子分别执行 BFS 会把本应同时发生的传播拆开，并且重复遍历网格。

## Approach

### Brute Force

- Idea: 对每个初始腐烂橘子单独做传播搜索。
- Complexity: 可能重复访问同一格子多次。
- Why it is not enough: 不能正确建模“所有起点同时向外扩张”的时间线。

### Optimized

- Core invariant: 一轮开始时，队列前 `level_size` 个坐标表示同一分钟内已经腐烂、等待传播的橘子。
- Data structure / state: `deque` 存坐标，`freshCnt` 存未腐烂橘子数，`minutes` 存已扩张的层数。
- Steps:

```text
1. 扫描网格，将所有初始腐烂橘子入队，并统计新鲜橘子。
2. 当 queue 非空且 freshCnt > 0 时，固定 level_size，让当前层同时传播并将 minutes 加一。
3. 只在橘子从 1 第一次变为 2 时入队并减少 freshCnt；最后根据 freshCnt 返回 minutes 或 -1。
```

## Complexity

- Time: `O(mn)`
- Space: `O(mn)` worst case
- Why: 每个格子最多被访问并入队一次；最坏时同一层可有 `O(mn)` 个橘子。

## Teach Back

- Key invariant: queue 中是最新腐烂、等待传播的橘子；固定 `level_size` 保证一次只处理当前一分钟。
- Why this data structure / state works: 所有初始起点共享同一个队列，因此 BFS 层数就是每个格子距离最近初始起点的时间。
- Complexity and tradeoff: 时间 `O(mn)`，队列空间最坏 `O(mn)`；代价是原地修改网格。
- Easiest edge case to miss: `[[2]]` 中队列非空但没有新鲜橘子；`freshCnt > 0` 的循环条件保证结果为 `0`。
- When this pattern does NOT apply: 多源 BFS 适合多个起点、等权传播的问题；传播代价不同时不能直接按 BFS 层数计时。

## Mistakes

- Mistake tag: `duplicate-handling`, `complexity-explanation-gap`
- Symptom: 初版会将任意值为 `2` 的邻居再次入队，并且一度将队列空间说成树高 `O(h)`。
- Root cause: 未将入队条件限定为状态首次从 `1 -> 2`，并误用了树题的空间记号。
- Fix: 只在新鲜橘子首次腐烂时标记并入队；根据队列最大容量分析网格 BFS 的空间。

## Pattern

- Pattern name: Multi-source BFS
- Related pattern note: `knowledge/patterns/graph.md`
- Similar problems: 542. 01 Matrix; 1162. As Far from Land as Possible
- Contrast: 200 每发现一个新连通分量就单独启动 BFS，而 994 将所有起点一次性入队，层数直接表示传播时间。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
