from typing import List
from collections import deque

class Solution:
    def isBipartite(self, graph: List[List[int]]) -> bool:
        q = deque()
        setA, setB = set(), set()

        for i, nodes in enumerate(graph):
            if i not in setA and i not in setB:
                setA.add(i)
                q.append(i)
            while q:
                curr = q.popleft()
                for node in graph[curr]:
                    if curr in setA:
                        if node in setA:
                            return False
                        elif node in setB:
                            continue
                        else:
                            setB.add(node)
                            q.append(node)
                    elif curr in setB:
                        if node in setB:
                            return False
                        elif node in setA:
                            continue
                        else:
                            setA.add(node)
                            q.append(node)
        return True
