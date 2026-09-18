# 双指针：同向（快慢）vs 对撞（两端收缩）

## 什么时候用

- **同向快慢指针**：原地压缩/分区数组——把满足条件的元素稳定地压到前缀（删元素、移零、去重）。
- **对撞指针（贪心支配型）**：在"选一对 (i, j)"的**最优化**问题里，若存在**支配论证**（dominance/exchange argument）——能证明某一端的当前元素不可能再参与更优解，就可以每步安全地丢弃一端，把 O(n²) 的配对枚举降为 O(n)。
- **对撞指针（有序搜索型）**：在**已排序**数组上找"和等于 target 的配对"。靠的不是贪心，而是**单调性**：`sum` 太大只能收右、太小只能进左，被跳过的配对已被证明不可能命中。这是 15 3Sum 内层用的那种。

## 核心不变量

- 同向（283 移动零）：任意时刻 `[0, slow)` 是已确认的非零前缀且保持原相对顺序，`[slow, fast)` 全是 0，`[fast, n)` 未探索。
- 对撞（11 盛水）：所有"已被指针跳过的配对"都已被证明 **不可能优于** 已记录的最大值。移动较矮一边的理由：固定较矮的 `h[l]` 不动、只把另一端往里收，`min` 不会超过 `h[l]` 而宽度必然减小，面积不可能变大 ⇒ 含 `l` 的所有剩余配对可整体丢弃。
- 有序搜索（15 3Sum 内层）：数组升序时 `nums[l] + nums[r]` 关于 `l` 递增、关于 `r` 递减。若 `sum > target`，则任何 `l' > l` 与当前 `r` 配对只会更大 ⇒ 含 `r` 的剩余配对全部无解，`r -= 1` 安全；反之同理。**每个下标最多被访问一次 ⇒ 内层 O(n)，整体 O(n²)。**

## 紧凑模板

```python
# 同向：稳定压缩前缀
slow = 0
for fast in range(len(nums)):
    if keep(nums[fast]):
        nums[slow], nums[fast] = nums[fast], nums[slow]
        slow += 1

# 对撞：贪心收缩
l, r = 0, len(a) - 1
best = 0
while l < r:
    best = max(best, score(l, r))
    if a[l] <= a[r]:
        l += 1        # 丢弃被支配的一端
    else:
        r -= 1

# 有序搜索 + 去重：kSum 的内层骨架（nums 已升序）
for i in range(len(nums)):
    if nums[i] > 0: break                       # 剪枝：后面全是正数，不可能凑出 0
    if i > 0 and nums[i] == nums[i-1]: continue  # 外层去重：与【前一个】比
    l, r = i + 1, len(nums) - 1
    while l < r:
        s = nums[i] + nums[l] + nums[r]
        if s < 0:   l += 1
        elif s > 0: r -= 1
        else:
            res.append([nums[i], nums[l], nums[r]])
            l += 1; r -= 1
            while l < r and nums[l] == nums[l-1]: l += 1  # 内层去重：两侧都要
            while l < r and nums[r] == nums[r+1]: r -= 1
```

## 常见错误

- 空间复杂度答成 O(n)：两种写法都是 **O(1)** 额外空间，原地是它们存在的意义（`complexity-explanation-gap`）。
- 以为 swap 分区是稳定分区：**swap 只对压缩到前面的那一类稳定**，被换到后面的一类顺序会乱。反例：`[2a,1,2b,3]` 把偶数换到后面 → `[1,3,2b,2a]`。283 里 0 全相同所以侥幸无感。
- 对撞指针不给贪心证明就上手：面试必问"为什么移矮的不漏解"，答不出等于没会（`tradeoff-gap`）。
- 相等时随便动哪边都对（11 题）：短板已定、宽度只减，当前两端各自的剩余配对都被支配。
- **外层去重比错方向**（15 题）：必须 `nums[i] == nums[i-1]` 与**前一个**比。若写成与后一个比，`[-1,-1,2]` 这类"重复值参与同一组解"会被整组跳掉。
- **只去重一侧**（15 题）：找到解后 `l`、`r` 两边都要跳过重复，否则 `[-2,0,0,2,2]` 会重复产出 `[-2,0,2]`。
- **`sorted(nums)` 不是原地排序**（15 题）：额外 O(n) 空间。要答 O(1) 得用 `nums.sort()`，且必须说"**除输出外**"（`complexity-explanation-gap` + `python-api-detail`）。
- **前缀/后缀数组版忘记空输入特判**（42 题）：`maxL[0] = height[0]` 在 `height == []` 时直接 IndexError，必须先 `if not height: return 0`。双指针版靠 `while l < r` 天然免疫——**这个健壮性差异本身就是可讲的对比点**。

## 与相邻模式的对比（决策边界）

- **对撞贪心成立的前提**：目标函数对被丢弃端是"瓶颈型/单调支配"的（如 `min(h[l],h[r])×宽`）。若换成 `(h[l]+h[r])×宽`，移矮的一边**不再安全**——里面一根高柱可能靠"和"补回宽度损失，贪心失效，需要换方法。
- **11 盛水 vs 42 接雨水 —— 分水岭是「求最值 vs 求和」**（面试高频对比）：
  - **求最值**（11）：某个候选一旦被证明"不可能更优"就能整体**丢弃**（支配论证）。
  - **求和**（42）：每一格的贡献都必须计入，**丢了就永远补不回来** ⇒ 双指针在这里不是丢弃，而是**结算**：每步把一格的水量锁死后再移动。
  - 42 的灵魂一步：`water[i] = min(maxL, maxR) - height[i]`，而当 `maxL < maxR` 时，**不必知道真实 maxR 的确切值**——只要知道它的**下界**已经超过 maxL，`min` 就被钉死在 maxL 上，`l` 这一格当场可结算。**用下界代替精确值**。
  - 判断条件写 `maxL < maxR` 比写 `height[l] < height[r]` 更好：前者正确性证明一行就完（`maxL < maxR ≤ 真实 maxR ⇒ min = maxL`），白板上更好讲。
- **滑动窗口**：也是同向双指针，但窗口两端都动、维护的是"窗口内性质"，与 283 的"分区压缩"不是一回事。
- **排序双指针 vs 哈希**（1 Two Sum / 167 Two Sum II / 15 3Sum）——一条决策链，背下来：
  1. **无序 + 要下标** ⇒ 哈希。排序会破坏下标（Two Sum 本尊）。
  2. **无序 + 要值且需去重** ⇒ 排序 + 双指针。空间更省，且去重退化为"跳过相邻相同值"，无需把三元组转 tuple 塞 set（3Sum）。
  3. **已有序** ⇒ 双指针。排序开销归零 ⇒ 时间与哈希打平（同 O(n)），**决胜维度变成空间：O(1) vs O(n)，双指针胜**。此时不自己排序，下标也天然保留（167 明确要求 constant extra space）。

## 关联题目

- 0283 Move Zeroes（同向，swap 压缩）
- 0011 Container With Most Water（对撞，贪心支配）
- 0015 3Sum（排序 + 有序搜索型对撞，双层去重）
- 0042 Trapping Rain Water（形似对撞，实为逐格结算；另有单调栈"横层"解法 → 见 [[monotonic-stack]]）
- 0167 Two Sum II（已有序 ⇒ 双指针，题目明确要求 O(1) 空间）

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 同向快慢指针 | complete | #283 Move Zeroes (complete) |
| 对撞与有序搜索 | complete | #11 Container With Most Water (complete); #15 3Sum (complete) |
| 支配淘汰与逐项结算 | complete | #42 Trapping Rain Water (complete) |

<!-- sweep-map:end -->
