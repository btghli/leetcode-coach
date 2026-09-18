from typing import List
import math

class Solution:
    def minSubArrayLen(self, target: int, nums: List[int]) -> int:
        left= 0
        _min = math.inf
        sum = 0
        for right in range(len(nums)):
            sum += nums[right]
            while sum >= target:
                _min = min(_min, right - left + 1)
                sum -= nums[left]
                left += 1
        return 0 if _min == math.inf else _min
