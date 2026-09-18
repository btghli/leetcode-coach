from typing import List
from collections import defaultdict, deque

class Solution:
    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        indegreeCnt = [0] * numCourses
        graph = defaultdict(list)
        for p in prerequisites:
            indegreeCnt[p[0]] += 1
            graph[p[1]].append(p[0])
            
        queue = deque([])
        for n in range(numCourses):
            if indegreeCnt[n] == 0:
                queue.append(n)
                
        solvedCourse = 0
        while queue:
            curr = queue.popleft()
            solvedCourse += 1
            for next in graph[curr]:
                indegreeCnt[next] -= 1
                if indegreeCnt[next] == 0:
                    queue.append(next)
        return solvedCourse == numCourses
