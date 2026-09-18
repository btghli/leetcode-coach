from typing import List

class Solution:
    def largestRectangleArea(self, heights: List[int]) -> int:
        stack = []
        _max = 0
        heights.append(0)
        for i, h in enumerate(heights):
            while len(stack) >= 1 and heights[stack[-1]] > h:
                height = heights[stack.pop()]
                right = i
                left = -1 if not stack else stack[-1]
                width = right - left - 1
                _max = max(_max, height * width)
            stack.append(i)
        return _max
