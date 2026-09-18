# Demo Conversation

用户：用 leetcode-coach，今天开始训练。

Coach：先恢复状态。

```bash
leetcode-coach status --brief
leetcode-coach plan
leetcode-coach chat --model <provider:model-id> --thread-id demo-session
```

Coach：今天先做 2 道 due review，再做 active list 的下一道新题。第一题用 `redo-from-memory`：先说 invariant，再写代码。

用户：Two Sum 的 invariant 是什么？

Coach：先不要看代码。你需要维护一个映射：已经见过的数 -> 下标。遍历到 `x` 时，只要 `target - x` 已经出现，就找到了答案。你来说明为什么不会错过答案。

用户：AC 了。

Coach：先做 teach-back；完成后，graph 会展示归档和进度写入参数供你批准、编辑或拒绝。

Coach：请用 30 秒回答：核心 invariant 是什么？复杂度为什么是 O(n)？最容易漏掉的边界是什么？

用户：讲完了。

Coach：LangGraph 展示一次 `complete_attempt` approval，其中包含 solution 归档、训练记录、复习日期、pattern sweep 和 session log。用户批准后整组执行；任何一步失败都会回滚本组学习数据，并保留 thread checkpoint。
