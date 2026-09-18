from typing import Optional


class TreeNode:
    def __init__(
        self,
        val: int = 0,
        left: Optional["TreeNode"] = None,
        right: Optional["TreeNode"] = None,
    ) -> None:
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def isValidBST(self, root: Optional[TreeNode]) -> bool:
        _max = float("-inf")
        def dfs(node) -> bool:
            nonlocal _max
            if node is None:
                return True
            
            if not dfs(node.left):
                return False
            
            if node.val <= _max:
                return False
            _max = node.val
            
            if not dfs(node.right):
                return False
            
            return True
        
        return dfs(root)
