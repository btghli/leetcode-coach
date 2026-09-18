from solution import Solution


def test_example():
    assert Solution().longestConsecutive([100, 4, 200, 1, 3, 2]) == 4


def test_example_with_duplicates():
    assert Solution().longestConsecutive([0, 3, 7, 2, 5, 8, 4, 6, 0, 1]) == 9


def test_empty():
    assert Solution().longestConsecutive([]) == 0


def test_single():
    assert Solution().longestConsecutive([42]) == 1


def test_all_duplicates():
    assert Solution().longestConsecutive([1, 1, 1, 2]) == 2


def test_negative_numbers():
    assert Solution().longestConsecutive([-2, -1, 0, 5]) == 3


if __name__ == "__main__":
    test_example()
    test_example_with_duplicates()
    test_empty()
    test_single()
    test_all_duplicates()
    test_negative_numbers()
    print("All tests passed.")
