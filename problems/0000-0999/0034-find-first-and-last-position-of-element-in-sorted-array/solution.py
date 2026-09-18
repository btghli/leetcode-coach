from typing import List

class Solution:
    def searchRange(self, nums: List[int], target: int) -> List[int]:
        # answers binary search 
        res = [-1, -1]
        
        lo, hi = 0, len(nums)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] >= target:
                hi = mid
            else:
                lo = mid + 1
        
        if lo == len(nums) or lo <= len(nums)-1 and nums[lo] != target:
            return res
        res[0] = lo
        
        lo, hi = lo + 1, len(nums)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] > target:
                hi = mid
            else:
                lo = mid + 1
        if lo-1 <= len(nums) - 1 and nums[lo-1] == target:
            res[1] = lo-1
        return res
