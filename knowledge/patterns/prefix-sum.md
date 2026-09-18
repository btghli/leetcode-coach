# 前缀和 / 差分

## 什么时候用

- **前缀和 (prefix sum)**：反复查询"区间和"，或问题可转化为"两个前缀之差"。信号：*子数组和 = k / 和能被 k 整除 / 区间和查询*。尤其当数组含负数、滑窗单调性失效时，它是滑窗的替补。
- **差分 (difference array)**：对数组做多次"区间 +v"更新、最后才查询。信号：*航班预订、区间加、会议室重叠计数*。
- **二维前缀和**：大量矩形区域求和，使用容斥把每次查询降为 O(1)。
- **前缀取模**：两个前缀余数相等时，它们的差可被 k 整除。

## 核心不变量

- 前缀和：`pre[i] = nums[0..i-1]` 之和（`pre[0]=0`）。则 `sum(i..j) = pre[j+1] - pre[i]`。"子数组和 = k" ⟺ 存在两个前缀之差为 k ⟹ 边扫边用哈希记录已见前缀和的次数/最早下标，O(n)。
- 差分：`diff[i] = a[i] - a[i-1]`。区间 `[l, r] += v` ⟺ `diff[l] += v; diff[r+1] -= v`。最后对 `diff` 求前缀和还原。把每次 O(区间长) 的更新降为 O(1)。
- 二维前缀：`pre[r][c]` 表示左上角半开矩形 `[0,r) × [0,c)`，任意矩形用四块容斥得到。

## 紧凑模板

```python
# 子数组和 = k 的个数（560），含负数也对
from collections import defaultdict
seen = defaultdict(int); seen[0] = 1     # 空前缀
pre = 0; ans = 0
for x in nums:
    pre += x
    ans += seen[pre - k]                 # 有多少个更早前缀能凑出 k
    seen[pre] += 1
return ans

# 差分：区间批量加
diff = [0] * (n + 1)
for l, r, v in updates:
    diff[l] += v
    diff[r + 1] -= v
res, cur = [], 0
for i in range(n):
    cur += diff[i]
    res.append(cur)
```

## 常见错误

- 忘记 `seen[0] = 1`（前缀本身正好等于 k 的情况漏掉）——最经典的坑。
- 记"最早下标"求最长子数组时，`seen` 里同一前缀和只存第一次出现的下标，别覆盖。
- 差分右端点写成 `diff[r]`：必须 `diff[r+1] -= v`，数组开 `n+1` 防越界。
- 有负数时不能用滑窗求"和=k"（呼应 209 的单调性）。
- Python 取模已经非负；跨语言时需要用 `(x % k + k) % k` 统一负余数。

## 对比

- vs **滑动窗口**：全正 + 求最短/最长 → 滑窗 O(1) 空间；含负数 / 求"恰好等于 k" → 前缀和 + 哈希 O(n) 空间。
- vs **树状数组/线段树**：前缀和只支持"先全部更新再查询"；边更新边查询要上树状数组。

## 相关题目

- 560 和为 K 的子数组（前缀和 + 哈希，含负数）
- 974 和可被 K 整除的子数组（前缀和取模）
- 1094 拼车 / 1109 航班预订统计（差分）
- 303 / 304 区域和检索（一维/二维前缀和）

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 一维区间查询 | 0/1 | #303 Range Sum Query - Immutable (todo) |
| 前缀和加哈希 | complete | #560 Subarray Sum Equals K (complete) |
| 前缀取模 | 0/1 | #974 Subarray Sums Divisible by K (todo) |
| 二维前缀和 | 0/1 | #304 Range Sum Query 2D - Immutable (todo) |
| 差分数组 | complete | #1109 Corporate Flight Bookings (complete) |

<!-- sweep-map:end -->
