from solution import Solution, TreeNode


def test_empty_tree():
    sol = Solution()
    assert sol.pathSum(None, 0) == 0


def test_paths_can_start_below_root():
    root = TreeNode(
        10,
        TreeNode(5, TreeNode(3, TreeNode(3), TreeNode(-2)), TreeNode(2, None, TreeNode(1))),
        TreeNode(-3, None, TreeNode(11)),
    )
    sol = Solution()
    assert sol.pathSum(root, 8) == 3


def test_negative_values():
    root = TreeNode(1, TreeNode(-2), TreeNode(-3))
    sol = Solution()
    assert sol.pathSum(root, -1) == 1
