# 二分查找：有序定位 + 答案二分

## 什么时候用

- **有序数组定位**：数组/矩阵有序（或旋转有序），找目标 / 插入位 / 边界。信号：*sorted、O(log n)、第一个 ≥ x 的位置*。
- **答案二分（二分答案）**：答案落在数值区间里，且有单调判定 `check(x)`（x 可行 ⇒ 更大/更小的也可行）。信号：*最小化最大值 / 最大化最小值 / 能否在 X 内完成*。

## 核心不变量

- 维护一个仍可能含答案的区间 `[lo, hi]`，每步用中点砍半，被丢弃的一半已被证明不含答案。
- 统一心法（找边界最稳）：把问题变成"找第一个满足 `check` 为真的位置"，用左闭右开 `[lo, hi)`：

```python
while lo < hi:
    mid = (lo + hi) // 2
    if check(mid): hi = mid      # mid 可能是答案，保留，收右
    else:          lo = mid + 1  # mid 不行，弃左半
return lo
```

## 紧凑模板

```python
# 1) 找第一个 >= target 的下标（lower_bound）
lo, hi = 0, len(a)          # 右开
while lo < hi:
    mid = (lo + hi) // 2
    if a[mid] >= target: hi = mid
    else:                lo = mid + 1
return lo                    # 可能 == len(a)，表示都比 target 小

# 2) 答案二分：check 单调
lo, hi = min_ans, max_ans
while lo < hi:
    mid = (lo + hi) // 2
    if feasible(mid): hi = mid   # mid 可行，试更小
    else:             lo = mid + 1
return lo
```

## 常见错误

- `mid = (lo+hi)//2` 配 `lo = mid`（不 +1）⇒ 死循环。收左半必须 `lo = mid + 1`。
- 闭区间 `[lo, hi]` 与右开 `[lo, hi)` 混用：循环条件、返回值、hi 初值要成套。
- 忘了 target 可能不存在 / 落在数组外，返回值要能表达"没找到 / 插末尾"。
- 答案二分没验证 `check` 单调性就套模板（`tradeoff-gap`）。

## 对比

- vs **双指针有序搜索**（3Sum 内层）：那个两端向中间利用双变量单调；二分是一维区间对折。
- vs **滑动窗口**：滑窗针对连续区间增量维护；二分针对有序/单调判定的对折搜索。

## 相关题目

- 34 在排序数组中查找元素的第一个和最后一个位置（lower_bound 用两次）
- 35 搜索插入位置
- 33 / 153 旋转排序数组
- 875 爱吃香蕉的珂珂 / 1011 传送带 / 410 分割数组最大值（答案二分）

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 有序定位与边界 | complete | #34 Find First and Last Position of Element in Sorted Array (complete) |
| 旋转有序数组 | 0/1 | #33 Search in Rotated Sorted Array (todo) |
| 峰值与局部单调性 | 0/1 | #162 Find Peak Element (todo) |
| 答案二分 | 1/2 | #875 Koko Eating Bananas (complete); #1011 Capacity To Ship Packages Within D Days (todo) |

<!-- sweep-map:end -->
