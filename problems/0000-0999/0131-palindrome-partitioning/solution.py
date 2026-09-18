from typing import List

class Solution:
    def partition(self, s: str) -> List[List[str]]:
        
        res = []
        def dfs(start: int, path: List[int]):
            if start == len(s):
                res.append(path.copy())
                return

            for end in range(start, len(s)):
                piece = s[start:end+1]

                if not is_pal(piece):
                    continue
                
                path.append(piece)
                dfs(end+1, path)
                path.pop()
                
        def is_pal(s: str) -> bool:
            if len(s) < 1:
                return False
            if len(s) == 1:
                return True
            l, r = 0, len(s)-1 
            while l < r:
                if s[l] != s[r]:
                    return False
                l += 1
                r -= 1
            return True
        
        dfs(0, [])

        return res
