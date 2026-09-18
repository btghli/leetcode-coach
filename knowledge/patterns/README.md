# LeetCode Pattern Atlas

本目录按“让暴力复杂度下降的核心机制”组织题型，而不是按题面标签或代码里出现的数据结构分类。

如果你面对陌生题还不知道该选哪个模式，先使用 [LeetCode 陌生题解题 Cheatsheet](../PROBLEM-SOLVING-CHEATSHEET.md)，从暴力方案和重复工作推导优化方向。

如果面试临近、需要快速复习，使用 [LeetCode 面试前两小时 Cheatsheet](../INTERVIEW-2H-CHEATSHEET.md)。

- 每道题可以有多个解法标签，但每次训练只指定一个 `primary pattern`。
- 顶层文件负责问题结构导航；文件内的二级模式才是 Pattern Sweep 的最小学习单元。
- 完成状态不以“看过/做过”为准，必须同时满足 AC、归档解法和完整 Teach-back。
- [PROGRESS.md](./PROGRESS.md) 是自动生成的可读进度；权威状态仍在 [`study/pattern-sweep.json`](../../study/pattern-sweep.json) 与各题 `note.md`。

## Navigation

### Ⅰ. 线性结构与扫描

| Pattern | 核心问题 |
| --- | --- |
| [数组与哈希](./array-hash.md) | 能否把值映射为次数、位置、分组或目标下标？ |
| [双指针](./two-pointers.md) | 能否用单调性、支配关系或分区安全移动边界？ |
| [滑动窗口](./sliding-window.md) | 连续区间约束能否随左右端点增量维护？ |
| [前缀和与差分](./prefix-sum.md) | 区间量能否化为两个前缀之差或端点事件？ |
| [栈与单调结构](./monotonic-stack.md) | 哪些上下文或候选尚未完成结算？ |
| [二分查找](./binary-search.md) | 搜索空间或可行性判定是否单调？ |
| [链表](./linked-list-two-pointers.md) | 如何在失去随机访问时保存并安全修改连接关系？ |
| [区间与扫描线](./greedy-intervals.md) | 排序端点后，哪些区间可以封口或淘汰？ |
| [堆与优先队列](./heap.md) | 是否只需持续维护下一批最优候选？ |

### Ⅱ. 递归与关系结构

| Pattern | 核心问题 |
| --- | --- |
| [树](./tree.md) | 递归函数应向下携带什么、向上返回什么？ |
| [图](./graph.md) | 节点何时被访问、连通或最终确定？ |
| [回溯](./backtracking.md) | 如何完整遍历选择树并安全剪枝？ |
| [Trie 与字符串匹配](./trie-string.md) | 如何复用公共前缀或已匹配状态？ |

### Ⅲ. 全局优化

| Pattern | 核心问题 |
| --- | --- |
| [贪心](./greedy.md) | 哪个局部状态能支配所有被丢弃历史？ |
| [动态规划](./dynamic-programming.md) | 哪个状态足以概括未来决策所需的历史？ |

### Ⅳ. 专项结构

| Pattern | 核心问题 |
| --- | --- |
| [矩阵与模拟](./matrix-simulation.md) | 如何显式维护方向、边界和同步状态？ |
| [位运算与数学](./bit-math.md) | 哪条代数恒等式能消除枚举？ |
| [数据结构设计](./data-structure-design.md) | 如何从操作复杂度倒推并同步多个底层结构？ |

## Classification Rules

1. **按解法归类，不按题号永久归类。** #215 用堆时属于 Heap，用 Quickselect 时属于排序与选择。
2. **表示形式不是主模式。** #200 输入是矩阵，但核心是 Graph Traversal；#54 才是 Matrix Simulation。
3. **实现形态不是充分条件。** 使用两个索引不等于 Two Pointers；如果核心是维护连续合法区间，应归 Sliding Window。
4. **组合题选择降复杂度的主机制。** #239 的主机制是 Monotonic Queue，窗口只是候选过期规则。
5. **相邻模式必须写决策边界。** Pattern Card 要说明什么时候使用、为什么正确、什么时候会失败。

## Card Contract

每张模式卡包含：

1. `Problem Shape`：题面信号和约束形状；
2. `Core Invariant`：运行过程中始终成立的性质；
3. `Why It Works`：覆盖或淘汰候选的正确性证明；
4. `Compact Template`：只保留骨架；
5. `Decision Boundary`：和相邻模式的分界；
6. `Representative Problems`：Anchor、Transfer、Contrast/Advanced；
7. `Teach-back Prompts`：不变量、复杂度、边界和不适用场景。

## Recommended Order

```text
数组/哈希 → 双指针 → 滑动窗口 → 前缀和
→ 栈 → 二分 → 链表 → 区间 → 堆
→ 树 → 图 → 回溯 → Trie
→ 贪心 → 动态规划
→ 矩阵/模拟 → 位运算/数学 → 数据结构设计
```
