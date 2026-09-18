# 链表双指针：固定间距、dummy node 与原地操作

## 什么时候用

- 题目要求从链表尾部数第 `n` 个节点，但只允许一次遍历。
- 需要删除、插入或反转节点，且希望原地完成。
- 需要合并、重排或复制非线性指针关系；关键是修改连接前保存后继。
- 信号词：*倒数第 N 个、一次遍历、原地、前驱节点、链表中点*。

## 核心不变量

对“删除倒数第 N 个节点”，让 `fast` 先走 `n + 1` 步（从 dummy node 起），再让 `fast`、`slow` 同步前进：

- 始终保持 `fast` 比 `slow` 超前 `n + 1` 个节点。
- 当 `fast` 到达 `None` 时，`slow` 正好停在待删除节点的前驱。
- `dummy -> head` 让“删除头结点”与其他删除统一，无须特殊分支。

## 紧凑模板

```python
dummy = ListNode(0, head)
slow = fast = dummy

for _ in range(n + 1):
    fast = fast.next

while fast:
    slow = slow.next
    fast = fast.next

slow.next = slow.next.next
return dummy.next

# 原地反转
prev, cur = None, head
while cur:
    nxt = cur.next       # 先保存，断链后仍能继续
    cur.next = prev
    prev, cur = cur, nxt
return prev
```

## 常见错误

- `fast` 只先走 `n` 步，却仍删除 `slow.next`：差一位，删错节点。
- 不用 dummy：删除头结点时 `slow` 没有前驱，容易写出额外分支或空指针。
- 混淆“`slow` 停在目标节点”与“`slow` 停在目标前驱”：先明确后续要操作的是 `slow` 还是 `slow.next`。
- 遍历到 `fast.next is None` 时继续移动两个指针：循环条件和间距定义必须配套。
- 反转时先改 `cur.next` 再保存旧后继，导致剩余链表永久丢失。
- 合并或重排后没有断开旧尾指针，可能制造环。

## 对比

- vs **快慢找环**：都用两个指针，但找环时距离会动态变化；这里固定间距是为了定位倒数位置或中点。
- vs **数组双指针**：链表无法随机访问；双指针的价值是不用额外数组也能保留位置关系。
- vs **两次遍历**：两次遍历更直观，但固定间距可在一次遍历与 `O(1)` 额外空间内完成。

## 相关题目

- 0019 Remove Nth Node From End of List（固定间距 + dummy）
- 0206 Reverse Linked List（原地改链）
- 0876 Middle of the Linked List（快慢指针定位中点）
- 0141 / 0142 Linked List Cycle（找环；见快慢找环模式卡）

<!-- sweep-map:start -->

## Sweep Map

| Subpattern | Status | Representative problems |
| --- | --- | --- |
| 固定间距与 dummy | complete | #19 Remove Nth Node From End of List (complete) |
| 快慢指针 | complete | #141 Linked List Cycle (complete) |
| 原地反转 | 0/2 | #206 Reverse Linked List (todo); #92 Reverse Linked List II (todo) |
| 合并与重排 | 0/2 | #21 Merge Two Sorted Lists (todo); #143 Reorder List (todo) |
| 非线性指针复制 | 0/1 | #138 Copy List with Random Pointer (todo) |

<!-- sweep-map:end -->
