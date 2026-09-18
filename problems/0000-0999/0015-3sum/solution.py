class Solution:
    def threeSum(self, nums: list[int]) -> list[list[int]]:
        nums = sorted(nums)
        result = []
        for i, n in enumerate(nums):
            if i-1 >= 0 and nums[i-1] == nums[i]:
                continue
            l, r = i + 1, len(nums) - 1
            while l < r:
                total = nums[i] + nums[l] + nums[r]
                if total == 0:
                    result.append([nums[i], nums[l], nums[r]])
                    l += 1
                    r -= 1
                    while l < r and nums[l] == nums[l-1]: l += 1
                    while l < r and nums[r] == nums[r+1]: r -= 1
                elif total < 0:
                    l += 1
                else:
                    r -= 1  
        return result
