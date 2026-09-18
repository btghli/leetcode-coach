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
    def pathSum(self, root: Optional[TreeNode], targetSum: int) -> int:
        res = 0
        count = {0: 1}
        def dfs(node, currSum):
            nonlocal res
            if node is None:
                return 
            currSum += node.val
            if (currSum - targetSum) in count:
                res += count.get(currSum - targetSum, 0)
            count[currSum] = count.get(currSum, 0) + 1
            
            dfs(node.left, currSum)
            dfs(node.right, currSum)
            
            count[currSum] -= 1
            currSum -= node.val
            return 
        
        dfs(root, 0)
        return res
