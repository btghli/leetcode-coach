from typing import List

class Solution:
    def findKthLargest(self, nums: List[int], k: int) -> int:
        
        def quickselect(l, r, target: int) -> int:
            pivot = nums[random.randrange(l, r+1)]
            lt, gt, i = l, r, l
            while i <= gt:
                if nums[i] < pivot:
                   nums[lt], nums[i] = nums[i], nums[lt]; lt += 1; i += 1;
                elif nums[i] > pivot:
                   nums[gt], nums[i] = nums[i], nums[gt]; gt -= 1;
                else:
                    i += 1;
            if target < lt:
                return quickselect(l, lt-1, target)
            elif target > gt:
                return quickselect(gt + 1 , r, target)
            else:
                return nums[lt]
            
        return quickselect(0, len(nums)- 1, len(nums) - k)
