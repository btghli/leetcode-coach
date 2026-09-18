from typing import List

class Solution:
    def minEatingSpeed(self, piles: List[int], h: int) -> int:
        def timeEllapsed(k) -> int:
            h = 0
            for p in piles:
                h += (p + k - 1) // k
            return h    
            
        lo, hi = 1, max(piles)
        while lo < hi:
            mid = (lo + hi) // 2
            if timeEllapsed(mid) <= h:
                hi = mid
            else:
                lo = mid + 1
        return lo
