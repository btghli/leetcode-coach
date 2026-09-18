from solution import Solution


def test_examples():
    assert Solution().findRedundantConnection([[1, 2], [1, 3], [2, 3]]) == [2, 3]


def test_redundant_edge_before_final_input_edge():
    edges = [[1, 2], [2, 3], [3, 4], [1, 4], [1, 5]]
    assert Solution().findRedundantConnection(edges) == [1, 4]


def test_long_cycle():
    edges = [[1, 2], [2, 3], [3, 4], [4, 5], [1, 5]]
    assert Solution().findRedundantConnection(edges) == [1, 5]


def test_balanced_merges():
    edges = [[1, 2], [3, 4], [1, 3], [2, 4]]
    assert Solution().findRedundantConnection(edges) == [2, 4]
