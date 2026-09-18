from solution import Solution


def normalize(triplets):
    """三元组内部已升序,组间排序后再比较,消除输出顺序差异。"""
    return sorted(sorted(t) for t in triplets)


def test_example():
    assert normalize(Solution().threeSum([-1, 0, 1, 2, -1, -4])) == normalize(
        [[-1, -1, 2], [-1, 0, 1]]
    )


# --- 用户设计的三类边界 ---


def test_all_zeros():
    # "only 0":大量重复,去重必须只留一组
    assert normalize(Solution().threeSum([0, 0, 0, 0])) == [[0, 0, 0]]


def test_all_negative():
    # "only minus numbers":无解,且触发 nums[i] > 0 剪枝之外的路径
    assert Solution().threeSum([-3, -2, -1]) == []


def test_all_same_nonzero():
    # "only same numbers":全同且非零,无解
    assert Solution().threeSum([2, 2, 2, 2]) == []


# --- 补充:去重压力与最小规模 ---


def test_duplicate_pressure():
    # 同一个 i 下有多组和为 0 的 pair,内层双向去重都要生效
    assert normalize(Solution().threeSum([-2, 0, 0, 2, 2, -2, 1, 1])) == normalize(
        [[-2, 0, 2], [-2, 1, 1]]
    )


def test_minimum_size():
    assert Solution().threeSum([0, 1, 1]) == []


if __name__ == "__main__":
    test_example()
    test_all_zeros()
    test_all_negative()
    test_all_same_nonzero()
    test_duplicate_pressure()
    test_minimum_size()
    print("All tests passed.")
