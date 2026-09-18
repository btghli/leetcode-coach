from typing import List

from collections import defaultdict
class Solution:
    def findRedundantConnection(self, edges: List[List[int]]) -> List[int]:
        parent = defaultdict(int)
        size = defaultdict(lambda: 1)
        
        def find(n) -> int:
            if parent[n] == 0:
                parent[n] = n
            if parent[n] != n:
                parent[n] = find(parent[n])
            return parent[n]
        
        for e in edges:
            rootA = find(e[0])
            rootB = find(e[1])
            if rootA == rootB:
                return e
            if size[rootA] < size[rootB]:
                rootA, rootB = rootB, rootA
            parent[rootB] = rootA
            size[rootA] += size[rootB]
        return
