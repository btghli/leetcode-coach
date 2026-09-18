from typing import List

class Solution:
    def findAnagrams(self, s: str, p: str) -> List[int]:
        target = [0] * 26
        for char in p:
            target[ord(char)-ord('a')] += 1
        curr = [0] * 26
        result = []
        for right, char in enumerate(s):
            curr[ord(char)-ord('a')] += 1
            if right >= len(p) - 1:
                if tuple(curr) == tuple(target):
                    result.append(right - len(p) + 1)
                curr[ord(s[right - len(p) + 1])-ord('a')] -= 1
        return result
