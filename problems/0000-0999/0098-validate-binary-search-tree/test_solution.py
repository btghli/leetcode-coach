from solution import Solution, TreeNode


def test_empty_tree():
    sol = Solution()
    assert sol.isValidBST(None)


def test_valid_bst():
    root = TreeNode(2, TreeNode(1), TreeNode(3))
    sol = Solution()
    assert sol.isValidBST(root)


def test_ancestor_violation():
    root = TreeNode(5, TreeNode(1), TreeNode(6, TreeNode(3), TreeNode(7)))
    sol = Solution()
    assert not sol.isValidBST(root)


def test_duplicate_is_invalid():
    root = TreeNode(2, TreeNode(2), TreeNode(3))
    sol = Solution()
    assert not sol.isValidBST(root)
