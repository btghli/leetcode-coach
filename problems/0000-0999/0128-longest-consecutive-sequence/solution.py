from typing import List

class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        num_set = set(nums)
        _max = 0
        
        for n in num_set:
            if n-1 not in num_set:
                curr = n
                length = 1
                while curr+1 in num_set:
                    curr += 1
                    length += 1
                _max = max(_max, length)
        return _max
