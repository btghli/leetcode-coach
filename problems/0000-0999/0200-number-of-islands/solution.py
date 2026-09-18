from typing import List
from collections import deque

class Solution:
    def numIslands(self, grid: List[List[str]]) -> int:
        count = 0
        next = [[-1, 0],[1, 0],[0, -1],[0, 1]]
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                if grid[i][j] == "1":
                    count += 1
                    grid[i][j] = "0"
                    queue = deque([[i, j]])
                    while queue:
                        curr = queue.popleft()
                        for d in next:
                            x, y = curr[0] + d[0], curr[1] + d[1]
                            if 0 <= x < len(grid) and 0 <= y < len(grid[0]) and grid[x][y] == "1":
                                grid[x][y] = "0"
                                queue.append([x, y])
        return count
