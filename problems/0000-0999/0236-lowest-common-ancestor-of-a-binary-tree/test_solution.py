from solution import Solution, TreeNode


def build_tree():
    root = TreeNode(3)
    root.left = TreeNode(5)
    root.right = TreeNode(1)
    root.left.left = TreeNode(6)
    root.left.right = TreeNode(2)
    return root


def test_targets_in_different_subtrees():
    root = build_tree()
    sol = Solution()
    assert sol.lowestCommonAncestor(root, root.left, root.right) is root


def test_one_target_is_ancestor():
    root = build_tree()
    sol = Solution()
    assert sol.lowestCommonAncestor(root, root.left, root.left.right) is root.left


def test_targets_below_same_subtree():
    root = build_tree()
    sol = Solution()
    assert sol.lowestCommonAncestor(root, root.left.left, root.left.right) is root.left
