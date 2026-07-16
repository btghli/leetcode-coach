from typing import List

class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        numsSet = set(nums)
        _max = 0
        for n in numsSet:
            if n - 1 not in numsSet:
                end = n + 1
                while end in numsSet:
                    end += 1
                _max = max(_max, end - n)
        return _max
