from typing import List
from collections import defaultdict

class Solution:
    def subarraySum(self, nums: List[int], k: int) -> int:
        seen = defaultdict(int)
        seen[0] = 1
        pre, ans = 0, 0
        for n in nums:
            pre += n
            ans += seen[pre - k]
            seen[pre] += 1
        return ans
