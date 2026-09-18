from __future__ import annotations

from typing import List, Optional


class TreeNode:
    def __init__(
        self,
        val: int = 0,
        left: Optional[TreeNode] = None,
        right: Optional[TreeNode] = None,
    ) -> None:
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def buildTree(self, preorder: List[int], inorder: List[int]) -> Optional[TreeNode]:
        if len(preorder) == 0:
            return None
        root = TreeNode(preorder[0])
        indexOfRoot = inorder.index(root.val)
        leftInorder = inorder[:indexOfRoot]
        rightInorder = inorder[indexOfRoot + 1 :]
        leftPreorder = preorder[1 : len(leftInorder) + 1]
        rightPreorder = preorder[len(leftInorder) + 1 :]

        root.left = self.buildTree(leftPreorder, leftInorder)
        root.right = self.buildTree(rightPreorder, rightInorder)
        return root
