class TreeNode:
    def __init__(self, x: int):
        self.val = x
        self.left = None
        self.right = None


class Solution:
    def lowestCommonAncestor(self, root: 'TreeNode', p: 'TreeNode', q: 'TreeNode') -> 'TreeNode':
        def dfs(node) ->  'TreeNode':
            if node is None:
                return None
            
            if node == p or node == q:
                return node
            
            left = dfs(node.left)
            right = dfs(node.right)
                
            
            if left is not None and right is not None:
                    return node
                
            return left if left is not None else right
        return dfs(root)
