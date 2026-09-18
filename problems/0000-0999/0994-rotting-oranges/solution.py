from typing import List
from collections import deque

class Solution:
    def orangesRotting(self, grid: List[List[int]]) -> int:
        queue = deque([])
        freshCnt = 0
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == 2: # rotten
                    queue.append([i,j])
                if grid[i][j] == 1: # fresh
                    freshCnt += 1
        
        next = [[1,0],[-1,0],[0,-1],[0,1]]   
        minutes = 0     
        while queue and freshCnt > 0:
            level_size = len(queue)
            minutes += 1
            for i in range(level_size):
                curr = queue.popleft()
                for d in next:
                    x, y = curr[0] + d[0], curr[1] + d[1]
                    if 0 <= x < len(grid) and 0 <= y < len(grid[0]):
                        if grid[x][y] == 1:
                            grid[x][y] = 2
                            freshCnt -= 1
                            queue.append([x,y])
        
        return minutes if freshCnt == 0 else -1
