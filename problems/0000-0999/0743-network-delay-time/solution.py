from typing import List
import heapq

class Solution:
    def networkDelayTime(self, times: List[List[int]], n: int, k: int) -> int:
        adj = [[] for _ in range(n+1)]
        for u, v, w in times:
            adj[u].append((v,w))

        dist = [float('inf')] * (n+1)
        dist[k] = 0

        pq = [(0, k)]

        while pq:
            dis, node = heapq.heappop(pq)

            if dis > dist[node]:
                continue

            for adjNode, wt in adj[node]:
                if dis + wt < dist[adjNode]:
                    dist[adjNode] = dis + wt
                    heapq.heappush(pq, (dist[adjNode], adjNode))
        ans = max(dist[1:])
        return -1 if ans == float('inf') else ans
