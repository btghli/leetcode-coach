from typing import List

class Solution:
    def merge(self, intervals: List[List[int]]) -> List[List[int]]:
        intervals = sorted(intervals, key = lambda x:x[0])
        res = [intervals[0]]
        for interval in intervals:
            start, end = interval[0], interval[1]
            if start > res[-1][1]:
                res.append(interval)
                continue
            elif end > res[-1][1]:
                res[-1][1] = end
                continue

        return res
