<!-- leetcode-meta
{
  "id": 207,
  "slug": "course-schedule",
  "title": "Course Schedule",
  "difficulty": "Medium",
  "tags": [],
  "lists": [],
  "status": "AC",
  "mastery": "ok",
  "last_practiced": "2026-08-16",
  "next_review": "2026-08-17",
  "mistake_tags": [
    "initialization-error",
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
    "leetcode": "https://leetcode.com/problems/course-schedule/",
    "leetcode_cn": "https://leetcode.cn/problems/course-schedule/"
  }
}
-->

# Course Schedule

- Link: https://leetcode.com/problems/course-schedule/
- Difficulty:
- Tags:
- Lists:

## Restatement

- Input: 课程总数，以及 `[course, prerequisite]` 形式的有向依赖。
- Output: 是否存在一个能完成所有课程的顺序。
- Constraints that matter: 课程编号是 `0 ... numCourses - 1`；孤立课程也必须计入完成数。

## Key Observations

- Observation 1: `[a, b]` 建模为边 `b -> a`，节点是课程。
- Observation 2: 存在任意长度的有向环时，环内课程无法被完成。
- Brute force bottleneck: 如果每完成一批课程都重新扫描所有依赖，会重复检查同一条边。

## Approach

### Brute Force

- Idea: 反复扫描未完成课程，寻找当前所有前置条件都已满足的课程。
- Complexity: 如果每轮都重新扫描所有边，最坏可达 `O(VE)`。
- Why it is not enough: 没有增量维护尚未解除的前置条件数。

### Optimized

- Core invariant: `indegreeCnt[x]` 始终表示课程 `x` 尚未完成的前置课程数量；只有归零才可入队。
- Data structure / state: 入度数组、从前置课程指向后续课程的邻接表、入度为零的队列和已完成计数。
- Steps:

```text
1. 按 prerequisite -> course 建图，并统计每门课的入度。
2. 将所有入度为 0 的课程入队；每完成一门课，减少它指向课程的入度。
3. 相邻课程入度降为 0 时入队；最后检查完成数是否等于 numCourses。
```

## Complexity

- Time: `O(V + E)`
- Space: `O(V + E)`
- Why: 每门课最多入队一次，每条依赖边只在起点出队时访问一次；入度与队列占 `O(V)`，邻接表占 `O(E)`。

## Teach Back

- Key invariant: 入度是当前尚未解除的前置条件数，归零才能安全完成该课程。
- Why this data structure / state works: 每完成一门课就沿出边解除一个条件；环内节点的入度无法被全部降为零。
- Complexity and tradeoff: 时间和空间都是 `O(V + E)`；邻接表避免了为每门课重新扫描全部边。
- Easiest edge case to miss: 未出现在 `prerequisites` 中的孤立课程入度为 0，应在第一轮入队，无需特别处理。
- When this pattern does NOT apply: 拓扑排序用于有向依赖的顺序或环检测，不用于连通分量或最短路问题。

## Mistakes

- Mistake tag: `initialization-error`, `complexity-explanation-gap`
- Symptom: 初次提交因 `defaultdict()` 未提供 factory 而在累加入度时发生 `KeyError`；复杂度一度写成 `O(VE)`。
- Root cause: 字典缺失 key 时没有整数默认值，且没有按“每节点一次、每边一次”累加分析。
- Fix: 密集课程编号使用 `[0] * numCourses`；复杂度分别计算节点和边的总访问次数。

## Pattern

- Pattern name: Topological Sort (Kahn's Algorithm)
- Related pattern note: `knowledge/patterns/graph.md`
- Similar problems: 210. Course Schedule II; 802. Find Eventual Safe States
- Contrast: BFS 连通性依靠 visited；Kahn 拓扑排序依靠入度表示未解除的前置条件。

## Review Log

| Date | Mode | Result | Quality | Hint Level | Notes | Next Review |
| --- | --- | --- | --- | --- | --- | --- |
