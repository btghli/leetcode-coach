from solution import Solution


def test_examples():
    grid = [[2, 1, 1], [1, 1, 0], [0, 1, 1]]
    assert Solution().orangesRotting(grid) == 4


def test_unreachable_fresh_orange():
    grid = [[2, 1, 1], [0, 1, 1], [1, 0, 1]]
    assert Solution().orangesRotting(grid) == -1


def test_no_fresh_oranges():
    assert Solution().orangesRotting([[2]]) == 0
    assert Solution().orangesRotting([[0]]) == 0


def test_no_rotten_source():
    assert Solution().orangesRotting([[1]]) == -1


def test_multiple_sources_share_one_timeline():
    grid = [[2, 1, 1, 1, 2]]
    assert Solution().orangesRotting(grid) == 2
