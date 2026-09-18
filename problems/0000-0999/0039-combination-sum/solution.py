from typing import List

class Solution:
    def combinationSum(self, candidates: List[int], target: int) -> List[List[int]]:
        candidates = sorted(candidates)
        res = []
        n = len(candidates)

        def dfs(prev, total: int, path: List[int]):
            if total == target:
                res.append(path.copy())
                return 

            for i in range(prev, n):
                if total + candidates[i] > target:
                    break

                path.append(candidates[i])
                dfs(i, total + candidates[i], path)

                path.pop()

        dfs(0, 0, [])

        return res
