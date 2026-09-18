from typing import List

class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        left = 0;
        for i, n in enumerate(nums):
            if n != 0:
                nums[left], nums[i] = nums[i], nums[left]
                left += 1
        return
