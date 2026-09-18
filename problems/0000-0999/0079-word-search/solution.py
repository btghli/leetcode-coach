from typing import List

class Solution:
    def exist(self, board: List[List[str]], word: str) -> bool:

        directions = [(-1,0),(1,0),(0,-1),(0,1)]
        def dfs(x,y,i: int) -> bool:
            if i >= len(word):
                return True

            if x < 0 or x >= len(board) or y < 0 or y >= len(board[0]):
                return False
            if board[x][y] != word[i]:
                return False
                
            has_next = False

            backup = board[x][y]
            board[x][y] = ''
            for d in directions:
                dx, dy = d
                nx, ny = x+dx, y+dy
                if dfs(nx,ny,i+1):
                    has_next = True
            
            board[x][y] = backup
            return has_next
        
        for x in range(len(board)):
            for y in range(len(board[0])):
                if board[x][y] == word[0]:
                    if dfs(x,y,0):
                        return True

        return False
