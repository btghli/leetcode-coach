from solution import Solution


def normalize(groups):
    """组内排序、组间排序,消除顺序差异后再比较。"""
    return sorted(sorted(g) for g in groups)


def test_examples():
    sol = Solution()
    assert normalize(sol.groupAnagrams(["eat", "tea", "tan", "ate", "nat", "bat"])) == normalize(
        [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]]
    )


def test_empty_string():
    sol = Solution()
    assert normalize(sol.groupAnagrams([""])) == [[""]]


def test_single_char():
    sol = Solution()
    assert normalize(sol.groupAnagrams(["a"])) == [["a"]]


def test_no_merge_across_strings():
    # 曾经的 bug:count 没有按字符串重置,["a", "b"] 会被错误分组
    sol = Solution()
    assert normalize(sol.groupAnagrams(["a", "b"])) == [["a"], ["b"]]


if __name__ == "__main__":
    test_examples()
    test_empty_string()
    test_single_char()
    test_no_merge_across_strings()
    print("All tests passed.")
