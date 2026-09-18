from typing import Optional

# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def getIntersectionNode(self, headA: ListNode, headB: ListNode) -> Optional[ListNode]:
        a, b = headA, headB
        a_switched, b_switched = False, False
        while a and b:
            if a == b:
                return a
            a = a.next
            b = b.next
            
            if not a and not a_switched:
                a = headB
                a_switched = True
            if not b and not b_switched:
                b = headA
                b_switched = True
        return None
