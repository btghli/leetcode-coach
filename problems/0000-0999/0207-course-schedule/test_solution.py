from solution import Solution


def test_examples():
    assert Solution().canFinish(2, [[1, 0]]) is True
    assert Solution().canFinish(2, [[1, 0], [0, 1]]) is False


def test_no_prerequisites():
    assert Solution().canFinish(3, []) is True


def test_isolated_course_is_counted():
    assert Solution().canFinish(3, [[1, 0]]) is True


def test_self_cycle():
    assert Solution().canFinish(1, [[0, 0]]) is False


def test_longer_cycle():
    prerequisites = [[1, 0], [2, 1], [0, 2]]
    assert Solution().canFinish(3, prerequisites) is False


def test_multiple_prerequisites():
    prerequisites = [[1, 0], [2, 0], [3, 1], [3, 2]]
    assert Solution().canFinish(4, prerequisites) is True
