from solution import Solution, TreeNode


def test_empty_tree():
    sol = Solution()
    assert sol.maxDepth(None) == 0


def test_single_node():
    sol = Solution()
    assert sol.maxDepth(TreeNode(1)) == 1


def test_unbalanced_tree():
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))
    sol = Solution()
    assert sol.maxDepth(root) == 3
