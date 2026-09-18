from typing import List

class Solution:
    def maxArea(self, height: List[int]) -> int:
        l, r = 0, len(height)-1
        _max = 0
        while l < r:
            width = r - l
            if height[l] < height[r]:
                _max = max(_max, height[l] * width)
                l += 1
            else:
                _max = max(_max, height[r] * width)
                r -= 1
        return _max
