# 滑动窗口：变长 + k-约束

## 什么时候用

- 求"**连续**子数组/子串"的最优或计数问题，且约束**单调可维护**：窗口变大时约束单向恶化、变小时单向恢复。信号词：*最长/最短/恰好/至多 k 个 …… 的连续区间*。
- 三种子型：
  - **定长窗口**：窗口大小固定（长度为 k 的最大和）。
  - **变长-求最长**：右扩到违反约束，再收左到重新合法。
  - **变长-求最短**：右扩到满足约束，再尽量收左压缩答案。
  - **恰好 K**：如果“恰好”难以直接维护，尝试 `exactly(k) = atMost(k) - atMost(k-1)`。

## 核心不变量

- 每一时刻 `[left, right]` 是**当前 right 结尾时仍满足约束的那一段**；`left` 只增不减、`right` 也只增 ⇒ 每个元素最多进窗一次、出窗一次 ⇒ **O(n)**。
- **"零重复"约束**（3 无重复最长子串）：可用 last-seen 下标**一步跳** `left = max(left, last[c] + 1)`。
- **"至多 k 种 / 某字符至多 k 次"约束**（438 / 76 / 340）：**不能跳**，用**计数哈希** + `while 违反: 移出 s[left]; left += 1` **一格格缩**。原因：破坏约束时无法预知跳到哪个下标才刚好合法。
- **恰好 k** 的计数通常不直接维护：`atMost(k)` 在右端固定时贡献 `right-left+1` 个合法子数组，两次相减得到恰好 k。

## 紧凑模板

```python
# 变长-求最长（count-based，通用）
from collections import defaultdict
cnt = defaultdict(int)
left = 0
best = 0
for right, c in enumerate(s):
    cnt[c] += 1
    while violated(cnt):          # 约束被打破
        cnt[s[left]] -= 1
        if cnt[s[left]] == 0:
            del cnt[s[left]]
        left += 1
    best = max(best, right - left + 1)
return best

# 变长-求最短（最小覆盖子串 76）
left = 0
best = inf
for right in range(n):
    include(s[right])
    while satisfied():            # 已满足，尽量缩
        best = min(best, right - left + 1)
        exclude(s[left]); left += 1
return 0 if best == inf else best

# 定长
for right in range(n):
    add(nums[right])
    if right >= k - 1:
        update(answer)
        remove(nums[right - k + 1])

# 恰好 K 个不同值
return at_most(k) - at_most(k - 1)
```

## 常见错误

- 求最长用 `if 违反` 而非 `while 违反`：一次可能要缩多格（`complexity-explanation-gap`）。
- 更新答案时机写反：求最长在**收缩后**更新，求最短在**满足时**更新。
- 空间答 O(n)：应是 `O(min(n, σ))`，σ = 字符集 / 不同元素数。
- 把 k-约束套上"零重复"的 max 跳转 ⇒ `left` 乱跳漏解（`pattern-boundary-gap`）。
- 忘记 `del` 计数为 0 的键 ⇒ `len(cnt)`（种类数）虚高。

## 对比

- vs **双指针对撞**：滑窗两指针**同向**、维护区间合法性；对撞两指针**相向**、靠支配/单调丢弃配对。
- vs **前缀和**：涉及负数或"恰好等于 target 的和"时滑窗单调性失效，改用**前缀和 + 哈希**。

## 相关题目

- 3 无重复字符最长子串（零重复跳跃版）
- 438 找异位词 / 567 字符串排列（定长 + 计数）
- 76 最小覆盖子串（变长求最短）
- 340 至多 K 种不同字符（变长求最长，k-约束）

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 零重复跳跃 | complete | #3 Longest Substring Without Repeating Characters (complete) |
| 定长计数 | complete | #438 Find All Anagrams in a String (complete) |
| 变长求最长与至多 K | 0/1 | #424 Longest Repeating Character Replacement (todo) |
| 变长求最短 | 1/2 | #209 Minimum Size Subarray Sum (complete); #76 Minimum Window Substring (todo) |
| 恰好 K 与 atMost 转化 | 0/1 | #992 Subarrays with K Different Integers (todo) |

<!-- sweep-map:end -->
