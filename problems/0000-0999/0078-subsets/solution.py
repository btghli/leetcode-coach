from typing import List

class Solution:
    def subsets(self, nums: List[int]) -> List[List[int]]:
        res = []

        def dfs(i: int, path: List[int]):
            if i == len(nums):
                res.append(path.copy())
                return

            dfs(i+1, path)
            path.append(nums[i])
            dfs(i+1, path)
            path.pop()

        dfs(0, [])

        return res
