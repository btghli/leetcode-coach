from solution import Solution


def preorder_values(node):
    return (
        []
        if node is None
        else [node.val] + preorder_values(node.left) + preorder_values(node.right)
    )


def inorder_values(node):
    return (
        []
        if node is None
        else inorder_values(node.left) + [node.val] + inorder_values(node.right)
    )


def assert_reconstruction(preorder, inorder):
    root = Solution().buildTree(preorder, inorder)
    assert preorder_values(root) == preorder
    assert inorder_values(root) == inorder


def test_empty_tree():
    assert_reconstruction([], [])


def test_balanced_tree():
    assert_reconstruction([3, 9, 20, 15, 7], [9, 3, 15, 20, 7])


def test_left_skewed_tree():
    assert_reconstruction([1, 2, 3, 4], [4, 3, 2, 1])
