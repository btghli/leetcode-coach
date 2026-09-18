from solution import Solution


def test_example():
    assert Solution().largestRectangleArea([2, 1, 5, 6, 2, 3]) == 10


def test_example2():
    assert Solution().largestRectangleArea([2, 4]) == 4


def test_empty():
    assert Solution().largestRectangleArea([]) == 0


def test_single():
    assert Solution().largestRectangleArea([5]) == 5


def test_zero_height():
    assert Solution().largestRectangleArea([0]) == 0


def test_monotonic_increasing():
    # 全程不触发 while,完全依赖收尾 flush
    assert Solution().largestRectangleArea([1, 2, 3, 4, 5]) == 9


def test_monotonic_decreasing():
    # 每一步都触发 while,栈最多只有一个元素
    assert Solution().largestRectangleArea([5, 4, 3, 2, 1]) == 9


def test_all_equal():
    # 等高:strict > 会让相等元素留在栈里,靠最左那根拿到完整宽度
    assert Solution().largestRectangleArea([3, 3, 3, 3]) == 12


def test_duplicates_with_valley():
    assert Solution().largestRectangleArea([2, 1, 2]) == 3


def test_plateau_between_walls():
    assert Solution().largestRectangleArea([1, 4, 4, 4, 1]) == 12


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All tests passed.")
