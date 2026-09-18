from solution import Solution


def test_example():
    assert Solution().trap([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6


def test_example2():
    assert Solution().trap([4, 2, 0, 3, 2, 5]) == 9


def test_empty():
    assert Solution().trap([]) == 0


def test_single():
    assert Solution().trap([5]) == 0


def test_two_bars():
    assert Solution().trap([2, 1]) == 0


def test_monotonic_increasing():
    # 单调递增:一滴水都存不住
    assert Solution().trap([1, 2, 3, 4, 5]) == 0


def test_monotonic_decreasing():
    assert Solution().trap([5, 4, 3, 2, 1]) == 0


def test_flat():
    assert Solution().trap([3, 3, 3, 3]) == 0


def test_single_valley():
    assert Solution().trap([3, 0, 3]) == 3


def test_max_in_middle():
    # 最高柱在中间,左右两侧各自成谷,考验 maxL/maxR 的结算方向
    assert Solution().trap([2, 0, 3, 0, 2]) == 4


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All tests passed.")
