from solution import Solution, TreeNode


def test_empty_tree():
    sol = Solution()
    assert sol.levelOrder(None) == []


def test_single_node():
    sol = Solution()
    assert sol.levelOrder(TreeNode(1)) == [[1]]


def test_multiple_levels():
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))
    sol = Solution()
    assert sol.levelOrder(root) == [[3], [9, 20], [15, 7]]
