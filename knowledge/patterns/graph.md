# 图：关系、连通性与路径

## Problem Shape

- 对象之间存在任意连接、依赖、传播、转换或成本关系。
- 输入可能是边列表、邻接表、矩阵或隐式状态图；矩阵不是自动归“模拟”。
- 目标常见为连通分量、最短步数、依赖顺序、动态合并或最小连接成本。
- 选算法前先确认四件事：图是有向还是无向、边是否带权、边权是否非负、目标是遍历/顺序/连通性/最短路中的哪一种。

## Core Invariant

- DFS/BFS 遍历：节点在入栈/入队时就标记为已发现，因此每个节点最多展开一次。
- 多源 BFS：所有起点同时作为第 `0` 层；一轮开始时的 `level_size` 个元素属于同一时间层。
- 拓扑排序：入度是尚未解除的前置条件数，入度为 0 才可输出。
- 并查集：每个集合由唯一 root 标识；`find(a) == find(b)` 当且仅当 `a` 和 `b` 已经连通。
- 二分图染色：每条已检查边的两端必须异色；未染色邻居获得与当前节点相反的颜色。
- Dijkstra：从堆中弹出的未过期最小距离已被最终确定（要求边权非负）。

## Why It Works

先把题目还原为节点和边，再根据边权、方向和查询类型选择算法。图题的关键不是“用 BFS 还是 DFS”，而是明确什么状态已经最终确定：遍历题在首次发现时防重，拓扑排序在入度归零时解除依赖，并查集用 root 代表连通分量，Dijkstra 依靠非负边权最终确定当前最小距离。

## Selection Guide

| Goal / signal | Pattern | Key state |
| --- | --- | --- |
| 统计或标记连通分量 | DFS/BFS 遍历 | `seen` / 原地标记 |
| 多个起点同时等权扩散 | 多源 BFS | 初始全部入队 + 分层 |
| 有向依赖顺序或有向环检测 | Kahn 拓扑排序 | `indegree` + 零入度队列 |
| 边持续加入时的连通性 | Union-Find | `parent` + `size/rank` |
| 节点能否分为两个互斥集合 | 二分图染色 | `color` / 两个集合 |
| 非负带权图的单源最短路 | Dijkstra | `dist` + 最小堆 |

## Compact Templates

### DFS/BFS traversal

```python
seen = {start}
q = deque([start])
while q:
    node = q.popleft()
    for nei in graph[node]:
        if nei not in seen:
            seen.add(nei)       # 入队时标记，避免重复入队
            q.append(nei)
```

### Multi-source BFS

```python
q = deque(all_sources)
steps = 0
while q and unfinished > 0:
    for _ in range(len(q)):
        node = q.popleft()
        for nei in neighbors(node):
            if is_unvisited(nei):
                mark(nei)       # 入队时改状态
                unfinished -= 1
                q.append(nei)
    steps += 1
```

### Topological sort (Kahn)

```python
q = deque(node for node in nodes if indegree[node] == 0)
processed = 0
while q:
    node = q.popleft()
    processed += 1
    for nei in graph[node]:
        indegree[nei] -= 1
        if indegree[nei] == 0:
            q.append(nei)
has_cycle = processed != len(nodes)
```

### Union-Find

```python
def find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]

def union(a, b):
    ra, rb = find(a), find(b)
    if ra == rb:
        return False
    if size[ra] < size[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    size[ra] += size[rb]
    return True
```

### Bipartite coloring

```python
color = [-1] * n
for start in range(n):           # 非连通图
    if color[start] != -1:
        continue
    color[start] = 0
    q = deque([start])
    while q:
        node = q.popleft()
        for nei in graph[node]:
            if color[nei] == -1:
                color[nei] = 1 - color[node]
                q.append(nei)
            elif color[nei] == color[node]:
                return False
```

### Dijkstra with lazy deletion

```python
dist = [float("inf")] * n
dist[start] = 0
pq = [(0, start)]                # (distance, node)

while pq:
    cur_dist, node = heappop(pq)
    if cur_dist > dist[node]:    # 过期 tuple
        continue
    for nei, weight in graph[node]:
        new_dist = cur_dist + weight
        if new_dist < dist[nei]:
            dist[nei] = new_dist
            heappush(pq, (new_dist, nei))
```

## Practiced Problems

| Subpattern | Problem | Reusable takeaway | Complexity |
| --- | --- | --- | --- |
| DFS/BFS 遍历 | #200 Number of Islands | 扫描到未访问陆地就发现新连通分量；入队时将 `"1"` 改为 `"0"` 防止重复入队。 | Time `O(mn)`, space `O(mn)` |
| 多源 BFS | #994 Rotting Oranges | 所有初始源一次性入队；固定 `level_size` 表示同一分钟，`freshCnt` 判断是否全部覆盖。 | Time `O(mn)`, space `O(mn)` |
| 拓扑排序 | #207 Course Schedule | `[course, prerequisite]` 建成 `prerequisite -> course`；零入度课程入队，最后用处理数检测环。 | Time/space `O(V+E)` |
| 并查集 | #684 Redundant Connection | 加边前若两端 root 相同，该边就形成环；路径压缩配合按 size 合并。 | Time `O(E·α(V))`, space `O(V)` |
| 二分图染色 | #785 Is Graph Bipartite? | 每条边两端必须异色；外层遍历所有节点以覆盖非连通图，同色冲突等价于存在奇环。 | Time `O(V+E)`, space `O(V)` |
| 带权最短路 | #743 Network Delay Time | 堆 tuple 必须是 `(distance, node)`；更短距离直接重新入堆，旧 tuple 弹出时用 `dist` 跳过。 | Time `O(V + E log V)`; space `O(V+E)` |

> #743 已 AC，但本段只沉淀知识；其 sweep 完成状态仍由结构化 teach-back、完整审批和同步结果决定。

## Common Mistakes

- BFS 出队才标记，导致同一节点被多次入队。
- 无向图建边只加一个方向。
- 多源问题从每个源分别 BFS，破坏“同时扩散”的时间层。
- 拓扑排序把依赖边方向建反，或遗漏初始的零入度/孤立节点。
- `defaultdict` 的 factory 不是 callable；密集编号的计数状态往往直接用 list 更稳定。
- Union-Find 只声明 `size/rank` 或路径压缩，却没有真正更新相应状态。
- 二分图只从一个起点染色，遗漏其他连通分量。
- Dijkstra 把 tuple 写成 `(node, distance)`，导致堆按节点编号而不是距离排序。
- Dijkstra 不跳过过期 tuple，或用在负权边上。单条负边已会破坏“弹出即确定”；只有负环才会让距离无限减小。
- 复杂度混淆：邻接表遍历是 `O(V+E)`，堆式 Dijkstra 额外支付每次 `push/pop` 的对数代价。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| Tree | 可能有环、多个父节点或任意连接 | 天然根结构且每节点唯一父关系 |
| DFS/BFS | 连通分量、可达性，或等权最短步数 | 边权不同时不能直接按 BFS 层数计算 |
| 多源 BFS | 多个起点、所有边等权、求最近层数 | 非负带权最短路用 Dijkstra |
| Topological Sort | 有向依赖的可行顺序或环检测 | 不用于无向连通分量或最短路 |
| Union-Find | 大量合并与连通性查询 | 需要具体路径、层数或遍历顺序 |
| Bipartite Coloring | 检查能否分成两个互斥集合/是否存在奇环 | 不能解决课程依赖顺序或一般 `k` 染色 |
| Dijkstra | 非负边权的单源最短路 | 有负权边时考虑 Bellman-Ford |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #200 Number of Islands | 隐式网格图的连通分量 |
| Transfer | #994 Rotting Oranges | 多起点同时扩散与 BFS 分层 |
| Transfer | #207 Course Schedule | 有向依赖与 Kahn 拓扑排序 |
| Transfer | #684 Redundant Connection | 动态合并、连通性与环检测 |
| Transfer | #785 Is Graph Bipartite? | 二染色、非连通图与奇环 |
| Advanced | #743 Network Delay Time | 非负带权最短路、堆 tuple 与惰性删除 |

## Teach-back Prompts

- 节点和边分别是什么，图是有向还是无向？
- 一个状态在何时被最终确定？
- 为什么要在入队时而不是出队时标记？
- 为什么多源 BFS 要先把所有起点入队？
- 入度、Union-Find root、二分图颜色和 Dijkstra `dist` 各自表示什么？
- 为什么 Dijkstra 可以保留过期 tuple，又为什么不能使用负权边？
- 当前问题的时间与空间复杂度分别由哪些状态或操作贡献？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| DFS/BFS 遍历 | complete | #200 Number of Islands (complete) |
| 多源 BFS | complete | #994 Rotting Oranges (complete) |
| 拓扑排序 | complete | #207 Course Schedule (complete) |
| 并查集 | complete | #684 Redundant Connection (complete) |
| 二分图与染色 | complete | #785 Is Graph Bipartite? (complete) |
| 带权最短路 | complete | #743 Network Delay Time (complete) |
| 最小生成树 | complete | #1584 Min Cost to Connect All Points (complete) |

<!-- sweep-map:end -->
