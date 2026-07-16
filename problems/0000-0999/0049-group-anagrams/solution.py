from typing import List

class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        groups = {}
        for s in strs:
            freq = [0] * 26
            for char in s:
                freq[ord(char) - ord('a')] += 1
            groups[tuple(freq)].append(s)
        result = []
        for k, v in groups:
            result.append(v)
        return result
