from solution import Solution


def test_examples():
    grid = [
        ["1", "1", "1", "1", "0"],
        ["1", "1", "0", "1", "0"],
        ["1", "1", "0", "0", "0"],
        ["0", "0", "0", "0", "0"],
    ]
    assert Solution().numIslands(grid) == 1


def test_multiple_islands():
    grid = [
        ["1", "1", "0", "0", "0"],
        ["1", "1", "0", "0", "0"],
        ["0", "0", "1", "0", "0"],
        ["0", "0", "0", "1", "1"],
    ]
    assert Solution().numIslands(grid) == 3


def test_diagonal_cells_are_not_connected():
    grid = [["1", "0"], ["0", "1"]]
    assert Solution().numIslands(grid) == 2


def test_all_water():
    grid = [["0", "0"], ["0", "0"]]
    assert Solution().numIslands(grid) == 0
