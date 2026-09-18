# 矩阵与模拟：把方向、边界和状态转移显式化

## Problem Shape

- 要按螺旋、对角线或指定方向遍历二维结构。
- 要原地旋转、翻转、标记整行整列，或同步更新每个格子的状态。
- 题目规则本身就是算法，难点在顺序和边界而非搜索最优值。

## Core Invariant

- 边界遍历中，`top/bottom/left/right` 包围尚未处理的矩形。
- 原地变换的每个交换步骤保持目标映射，且不会读取已被破坏的旧值。
- 同步模拟必须区分旧状态与新状态，可用副本或额外编码同时保存二者。

## Why It Works

将方向和阶段写成有限状态机，每一步只处理当前尚未覆盖的边界或单元；对原地更新，证明编码能从更新后的值恢复旧状态。

## Compact Template

```python
top, bottom, left, right = 0, rows - 1, 0, cols - 1
while top <= bottom and left <= right:
    visit_top()
    top += 1
    visit_right()
    right -= 1
    if top <= bottom:
        visit_bottom()
        bottom -= 1
    if left <= right:
        visit_left()
        left += 1
```

## Common Mistakes

- 单行或单列时重复访问。
- 行列索引混用，非方阵样例才暴露错误。
- 原地更新后用新值计算邻居，破坏同步语义。
- 把所有矩阵题都归模拟；连通性和最短路仍属于图。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| 图遍历 | 规则是方向、边界或直接状态演化 | 目标是连通性、传播层数或路径 |
| 二维 DP | 每格按显式规则更新 | 每格代表子问题最优值/方案数 |
| 二维前缀 | 要遍历或原地变换 | 多次矩形区域聚合查询 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #54 Spiral Matrix | 收缩未处理边界 |
| Transfer | #48 Rotate Image | 坐标映射与原地分解变换 |
| Advanced | #289 Game of Life | 同步状态的双编码 |

## Teach-back Prompts

- 哪些变量精确定义尚未处理区域？
- 为什么原地更新不会污染后续读取？
- 当前题是模拟，还是矩阵表示的图/DP？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 边界与方向遍历 | 0/1 | #54 Spiral Matrix (todo) |
| 原地矩阵变换 | 0/1 | #48 Rotate Image (todo) |
| 行列标记 | 0/1 | #73 Set Matrix Zeroes (todo) |
| 状态模拟 | 0/1 | #289 Game of Life (todo) |

<!-- sweep-map:end -->
