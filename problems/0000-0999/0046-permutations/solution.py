from typing import List

class Solution:
    def permute(self, nums: List[int]) -> List[List[int]]:
        n = len(nums)
        used = [False] * n
        res = []
        
        def dfs(path: List[int]):
            if len(path) == len(nums):
                res.append(path.copy())
                return
            
            for i in range(n):
                if used[i]:
                    continue
                path.append(nums[i])
                used[i] = True
                dfs(path)
                path.pop()
                used[i] = False

        dfs([])
            
        return res
