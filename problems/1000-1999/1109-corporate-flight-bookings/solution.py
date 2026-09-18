from typing import List

class Solution:
    def corpFlightBookings(self, bookings: List[List[int]], n: int) -> List[int]:
        diff = [0] * (n + 2)
        for l,r,v in bookings:
            diff[l] += v
            diff[r+1] -= v
        res, cur = [], 0
        for i in range(1, n+1):
            cur += diff[i]
            res.append(cur)
        return res
