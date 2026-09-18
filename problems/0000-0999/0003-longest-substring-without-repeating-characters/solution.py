class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        last_seen = {}
        left = 0
        _max = 0
        for i, c in enumerate(s):
            offset = ord(c) - ord('a')
            if offset in last_seen:
                left = max(left, last_seen[offset] + 1)
            last_seen[offset] = i
            _max = max(_max, i - left + 1) 
        return _max
