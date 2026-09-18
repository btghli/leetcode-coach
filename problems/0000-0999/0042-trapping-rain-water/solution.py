from typing import List

class Solution:
    def trap(self, height: List[int]) -> int:
        # version Two Array
        # maxL = [0] * len(height)
        # maxL[0] = height[0]
        # for i in range(1, len(height)):
        #     maxL[i] = max(maxL[i-1], height[i])
        
        # maxR = [0] * len(height)
        # maxR[len(height)-1] = height[len(height)-1]
        # for i in range(len(height)-2, -1, -1):
        #     maxR[i] = max(maxR[i+1], height[i])
        
        # water = 0
        # for i in range(0, len(height)):
        #     water += min(maxL[i], maxR[i]) - height[i]
        # return water
        
        # version Two Pointers
        l, r = 0, len(height)-1
        maxL, maxR = 0, 0
        water = 0
        while l < r:
            maxL = max(maxL, height[l])
            maxR = max(maxR, height[r])
            if maxL < maxR:
                water += maxL - height[l]
                l += 1
            else:
                water += maxR - height[r]
                r -= 1
        return water
