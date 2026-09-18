# 位运算与数学：利用代数恒等式消除枚举

## Problem Shape

- 题目涉及二进制位、奇偶、子集掩码、唯一元素、快速幂、整除、质数或坐标关系。
- 数据范围提示逐个枚举或普通乘法过慢，但存在可组合的代数性质。

## Core Invariant

- XOR 满足交换、结合、自反消元：`x ^ x = 0`、`x ^ 0 = x`。
- 位掩码的第 `i` 位唯一表示第 `i` 个布尔状态。
- 快速幂每步保持 `answer * base**exponent` 等于原目标值。
- 几何题应使用规范化整数方向，避免浮点斜率误差。

## Why It Works

代数结构允许重排、分解或消去重复贡献；位运算将多个布尔状态压进一个整数；数学推导把线性或指数枚举降为对数或筛法复杂度。

## Compact Template

```python
ans = 1
while n:
    if n & 1:
        ans *= x
    x *= x
    n >>= 1
return ans
```

## Common Mistakes

- Python 负数右移和无限符号位语义与固定宽度整数不同。
- 位运算优先级不熟，复杂表达式没有加括号。
- 浮点斜率导致本应相等的方向键不相等。
- 模运算中先除法后取模，破坏整数可逆条件。

## Decision Boundary

| Nearby Pattern | Use This When | Use That When |
| --- | --- | --- |
| Hash Map | 有消元/位状态恒等式 | 需要保存任意值的次数或位置 |
| 状压 DP | 掩码只是集合表示 | 掩码状态之间还要做最优转移 |
| 二分答案 | 指数通过代数分解 | 答案值域具有单调可行性 |

## Representative Problems

| Role | Problem | Why it belongs here |
| --- | --- | --- |
| Anchor | #136 Single Number | XOR 成对消元 |
| Transfer | #50 Pow(x, n) | 指数按二进制分解 |
| Advanced | #149 Max Points on a Line | 方向向量规范化 |

## Teach-back Prompts

- 使用了哪条代数恒等式？
- 整数宽度、符号和溢出是否影响语言实现？
- 为什么整数规范化比浮点比较可靠？

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| XOR 消元 | 0/1 | #136 Single Number (todo) |
| 位计数与掩码 | 0/2 | #191 Number of 1 Bits (todo); #338 Counting Bits (todo) |
| 快速幂与分解 | 0/1 | #50 Pow(x, n) (todo) |
| 数论与筛法 | 0/1 | #204 Count Primes (todo) |
| 坐标与斜率 | 0/1 | #149 Max Points on a Line (todo) |

<!-- sweep-map:end -->
