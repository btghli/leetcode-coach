"""Canonical pattern curriculum, coverage, selection, and synchronization."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

META_RE = re.compile(r"<!--\s*leetcode-meta\s*(\{.*?\})\s*-->", re.S)
START = "<!-- sweep-map:start -->"
END = "<!-- sweep-map:end -->"
VERSION = 1

P = lambda id, slug, title, difficulty: {"id": id, "slug": slug, "title": title, "difficulty": difficulty}

CATALOG = [
    ("array-hash", "数组与哈希", "array-hash.md", [
        ("frequency-index", "计数与索引", [P(1, "two-sum", "Two Sum", "Easy"), P(49, "group-anagrams", "Group Anagrams", "Medium")]),
        ("set-dedup", "集合去重与连续性", [P(128, "longest-consecutive-sequence", "Longest Consecutive Sequence", "Medium")]),
        ("index-placement", "下标归位与原地标记", [P(41, "first-missing-positive", "First Missing Positive", "Hard"), P(448, "find-all-numbers-disappeared-in-an-array", "Find All Numbers Disappeared in an Array", "Easy")]),
        ("prefix-suffix-aggregate", "前后缀聚合", [P(238, "product-of-array-except-self", "Product of Array Except Self", "Medium")]),
        ("sort-select", "排序、分区与选择", [P(75, "sort-colors", "Sort Colors", "Medium")]),
    ]),
    ("two-pointers", "双指针", "two-pointers.md", [
        ("same-direction", "同向快慢指针", [P(283, "move-zeroes", "Move Zeroes", "Easy")]),
        ("opposite-direction", "对撞与有序搜索", [P(11, "container-with-most-water", "Container With Most Water", "Medium"), P(15, "3sum", "3Sum", "Medium")]),
        ("dominance-settlement", "支配淘汰与逐项结算", [P(42, "trapping-rain-water", "Trapping Rain Water", "Hard")]),
    ]),
    ("sliding-window", "滑动窗口", "sliding-window.md", [
        ("no-repeat", "零重复跳跃", [P(3, "longest-substring-without-repeating-characters", "Longest Substring Without Repeating Characters", "Medium")]),
        ("fixed-count", "定长计数", [P(438, "find-all-anagrams-in-a-string", "Find All Anagrams in a String", "Medium")]),
        ("variable-longest", "变长求最长与至多 K", [P(424, "longest-repeating-character-replacement", "Longest Repeating Character Replacement", "Medium")]),
        ("variable-shortest", "变长求最短", [P(209, "minimum-size-subarray-sum", "Minimum Size Subarray Sum", "Medium"), P(76, "minimum-window-substring", "Minimum Window Substring", "Hard")]),
        ("exactly-k", "恰好 K 与 atMost 转化", [P(992, "subarrays-with-k-different-integers", "Subarrays with K Different Integers", "Hard")]),
    ]),
    ("prefix-sum", "前缀和与差分", "prefix-sum.md", [
        ("range-query", "一维区间查询", [P(303, "range-sum-query-immutable", "Range Sum Query - Immutable", "Easy")]),
        ("prefix-hash", "前缀和加哈希", [P(560, "subarray-sum-equals-k", "Subarray Sum Equals K", "Medium")]),
        ("prefix-modulo", "前缀取模", [P(974, "subarray-sums-divisible-by-k", "Subarray Sums Divisible by K", "Medium")]),
        ("two-dimensional-prefix", "二维前缀和", [P(304, "range-sum-query-2d-immutable", "Range Sum Query 2D - Immutable", "Medium")]),
        ("difference-array", "差分数组", [P(1109, "corporate-flight-bookings", "Corporate Flight Bookings", "Medium")]),
    ]),
    ("binary-search", "二分查找", "binary-search.md", [
        ("boundary-search", "有序定位与边界", [P(34, "find-first-and-last-position-of-element-in-sorted-array", "Find First and Last Position of Element in Sorted Array", "Medium")]),
        ("rotated-search", "旋转有序数组", [P(33, "search-in-rotated-sorted-array", "Search in Rotated Sorted Array", "Medium")]),
        ("peak-search", "峰值与局部单调性", [P(162, "find-peak-element", "Find Peak Element", "Medium")]),
        ("answer-search", "答案二分", [P(875, "koko-eating-bananas", "Koko Eating Bananas", "Medium"), P(1011, "capacity-to-ship-packages-within-d-days", "Capacity To Ship Packages Within D Days", "Medium")]),
    ]),
    ("linked-list", "链表", "linked-list-two-pointers.md", [
        ("fixed-gap", "固定间距与 dummy", [P(19, "remove-nth-node-from-end-of-list", "Remove Nth Node From End of List", "Medium")]),
        ("fast-slow", "快慢指针", [P(141, "linked-list-cycle", "Linked List Cycle", "Easy")]),
        ("in-place-reversal", "原地反转", [P(206, "reverse-linked-list", "Reverse Linked List", "Easy"), P(92, "reverse-linked-list-ii", "Reverse Linked List II", "Medium")]),
        ("merge-and-reorder", "合并与重排", [P(21, "merge-two-sorted-lists", "Merge Two Sorted Lists", "Easy"), P(143, "reorder-list", "Reorder List", "Medium")]),
        ("random-links", "非线性指针复制", [P(138, "copy-list-with-random-pointer", "Copy List with Random Pointer", "Medium")]),
    ]),
    ("monotonic-structures", "栈与单调结构", "monotonic-stack.md", [
        ("syntax-stack", "括号与嵌套结构", [P(20, "valid-parentheses", "Valid Parentheses", "Easy")]),
        ("evaluation-stack", "表达式求值", [P(150, "evaluate-reverse-polish-notation", "Evaluate Reverse Polish Notation", "Medium")]),
        ("supporting-stack", "辅助栈维护极值", [P(155, "min-stack", "Min Stack", "Medium")]),
        ("next-element", "单调栈：相邻更大/更小", [P(739, "daily-temperatures", "Daily Temperatures", "Medium"), P(84, "largest-rectangle-in-histogram", "Largest Rectangle in Histogram", "Hard")]),
        ("monotonic-queue", "单调队列：窗口极值", [P(239, "sliding-window-maximum", "Sliding Window Maximum", "Hard")]),
    ]),
    ("heap", "堆与优先队列", "heap.md", [
        ("top-k", "Top K", [P(215, "kth-largest-element-in-an-array", "Kth Largest Element in an Array", "Medium")]),
        ("multiway-merge", "多路合并", [P(23, "merge-k-sorted-lists", "Merge k Sorted Lists", "Hard")]),
        ("two-heaps", "双堆与动态中位数", [P(295, "find-median-from-data-stream", "Find Median from Data Stream", "Hard")]),
        ("heap-scheduling", "任务调度与重组", [P(621, "task-scheduler", "Task Scheduler", "Medium")]),
    ]),
    ("tree", "树", "tree.md", [
        ("tree-dfs", "DFS 与后序聚合", [P(104, "maximum-depth-of-binary-tree", "Maximum Depth of Binary Tree", "Easy")]),
        ("tree-path", "路径状态", [P(437, "path-sum-iii", "Path Sum III", "Medium")]),
        ("tree-bfs", "层序 BFS", [P(102, "binary-tree-level-order-traversal", "Binary Tree Level Order Traversal", "Medium")]),
        ("bst-order", "BST 有序性", [P(98, "validate-binary-search-tree", "Validate Binary Search Tree", "Medium")]),
        ("lowest-common-ancestor", "最近公共祖先", [P(236, "lowest-common-ancestor-of-a-binary-tree", "Lowest Common Ancestor of a Binary Tree", "Medium")]),
        ("tree-construction", "构造与序列化", [P(105, "construct-binary-tree-from-preorder-and-inorder-traversal", "Construct Binary Tree from Preorder and Inorder Traversal", "Medium")]),
    ]),
    ("graph", "图", "graph.md", [
        ("traversal", "DFS/BFS 遍历", [P(200, "number-of-islands", "Number of Islands", "Medium")]),
        ("multi-source-bfs", "多源 BFS", [P(994, "rotting-oranges", "Rotting Oranges", "Medium")]),
        ("topological-sort", "拓扑排序", [P(207, "course-schedule", "Course Schedule", "Medium")]),
        ("union-find", "并查集", [P(684, "redundant-connection", "Redundant Connection", "Medium")]),
        ("bipartite", "二分图与染色", [P(785, "is-graph-bipartite", "Is Graph Bipartite?", "Medium")]),
        ("shortest-path", "带权最短路", [P(743, "network-delay-time", "Network Delay Time", "Medium")]),
        ("minimum-spanning-tree", "最小生成树", [P(1584, "min-cost-to-connect-all-points", "Min Cost to Connect All Points", "Medium")]),
    ]),
    ("backtracking", "回溯", "backtracking.md", [
        ("subsets", "子集与选择", [P(78, "subsets", "Subsets", "Medium")]),
        ("permutations", "排列与使用标记", [P(46, "permutations", "Permutations", "Medium")]),
        ("combinations", "组合与候选起点", [P(39, "combination-sum", "Combination Sum", "Medium")]),
        ("partition-search", "切割与分段", [P(131, "palindrome-partitioning", "Palindrome Partitioning", "Medium")]),
        ("board-search", "棋盘搜索与约束传播", [P(79, "word-search", "Word Search", "Medium")]),
    ]),
    ("greedy-intervals", "区间与扫描线", "greedy-intervals.md", [
        ("interval-merge", "区间合并", [P(56, "merge-intervals", "Merge Intervals", "Medium"), P(57, "insert-interval", "Insert Interval", "Medium")]),
        ("interval-intersection", "区间交集", [P(986, "interval-list-intersections", "Interval List Intersections", "Medium")]),
        ("interval-scheduling", "区间调度", [P(435, "non-overlapping-intervals", "Non-overlapping Intervals", "Medium")]),
        ("overlap-count", "重叠计数与会议室", [P(253, "meeting-rooms-ii", "Meeting Rooms II", "Medium")]),
    ]),
    ("greedy", "贪心", "greedy.md", [
        ("reachability-frontier", "最远可达边界", [P(55, "jump-game", "Jump Game", "Medium")]),
        ("local-contribution", "局部贡献与重置", [P(134, "gas-station", "Gas Station", "Medium")]),
    ]),
    ("dynamic-programming", "动态规划", "dynamic-programming.md", [
        ("one-dimensional", "一维状态", [P(70, "climbing-stairs", "Climbing Stairs", "Easy")]),
        ("knapsack", "背包", [P(416, "partition-equal-subset-sum", "Partition Equal Subset Sum", "Medium")]),
        ("grid-dp", "网格 DP", [P(62, "unique-paths", "Unique Paths", "Medium")]),
        ("two-sequence", "双序列 DP", [P(1143, "longest-common-subsequence", "Longest Common Subsequence", "Medium")]),
        ("subsequence", "子序列", [P(300, "longest-increasing-subsequence", "Longest Increasing Subsequence", "Medium")]),
        ("state-machine", "状态机 DP", [P(309, "best-time-to-buy-and-sell-stock-with-cooldown", "Best Time to Buy and Sell Stock with Cooldown", "Medium")]),
        ("interval-dp", "区间 DP", [P(516, "longest-palindromic-subsequence", "Longest Palindromic Subsequence", "Medium")]),
    ]),
    ("trie-string", "Trie 与字符串匹配", "trie-string.md", [
        ("prefix-trie", "前缀树", [P(208, "implement-trie-prefix-tree", "Implement Trie (Prefix Tree)", "Medium")]),
        ("wildcard-trie", "Trie 与通配符", [P(211, "design-add-and-search-words-data-structure", "Design Add and Search Words Data Structure", "Medium")]),
        ("trie-dfs", "Trie 与 DFS", [P(212, "word-search-ii", "Word Search II", "Hard")]),
        ("exact-string-match", "精确字符串匹配", [P(28, "find-the-index-of-the-first-occurrence-in-a-string", "Find the Index of the First Occurrence in a String", "Easy")]),
        ("rolling-hash", "滚动哈希", [P(187, "repeated-dna-sequences", "Repeated DNA Sequences", "Medium")]),
    ]),
    ("matrix-simulation", "矩阵与模拟", "matrix-simulation.md", [
        ("boundary-traversal", "边界与方向遍历", [P(54, "spiral-matrix", "Spiral Matrix", "Medium")]),
        ("in-place-transform", "原地矩阵变换", [P(48, "rotate-image", "Rotate Image", "Medium")]),
        ("matrix-marking", "行列标记", [P(73, "set-matrix-zeroes", "Set Matrix Zeroes", "Medium")]),
        ("state-simulation", "状态模拟", [P(289, "game-of-life", "Game of Life", "Medium")]),
    ]),
    ("bit-math", "位运算与数学", "bit-math.md", [
        ("xor-cancellation", "XOR 消元", [P(136, "single-number", "Single Number", "Easy")]),
        ("bit-counting", "位计数与掩码", [P(191, "number-of-1-bits", "Number of 1 Bits", "Easy"), P(338, "counting-bits", "Counting Bits", "Easy")]),
        ("fast-power", "快速幂与分解", [P(50, "powx-n", "Pow(x, n)", "Medium")]),
        ("number-theory", "数论与筛法", [P(204, "count-primes", "Count Primes", "Medium")]),
        ("geometry", "坐标与斜率", [P(149, "max-points-on-a-line", "Max Points on a Line", "Hard")]),
    ]),
    ("data-structure-design", "数据结构设计", "data-structure-design.md", [
        ("constant-time-composition", "均摊 O(1) 结构组合", [P(380, "insert-delete-getrandom-o1", "Insert Delete GetRandom O(1)", "Medium")]),
        ("cache-design", "缓存淘汰", [P(146, "lru-cache", "LRU Cache", "Medium")]),
        ("time-index", "时间索引", [P(981, "time-based-key-value-store", "Time Based Key-Value Store", "Medium")]),
        ("queue-design", "队列与环形缓冲区", [P(622, "design-circular-queue", "Design Circular Queue", "Medium")]),
        ("range-design", "区间结构", [P(715, "range-module", "Range Module", "Hard")]),
    ]),
]


def root(args):
    if args.root:
        return Path(args.root).resolve()
    for path in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
        if (path / "problems").exists() and (path / "study").exists():
            return path
    raise SystemExit("Study repository not found; pass --root.")


def date(): return dt.date.today().isoformat()
def state_path(r): return r / "study" / "pattern-sweep.json"
def progress_path(r): return r / "knowledge" / "patterns" / "PROGRESS.md"
def pattern_path(r, category):
    filename = category["pattern_file"] if isinstance(category, dict) else category[2]
    return r / "knowledge" / "patterns" / filename


def default_state():
    return {"version": VERSION, "current_focus": None, "categories": [
        {"slug": slug, "title": title, "pattern_file": file, "started_at": None, "completed_at": None,
         "subpatterns": [{"slug": ss, "title": st, "started_at": None, "completed_at": None, "problems": ps} for ss, st, ps in subs]}
        for slug, title, file, subs in CATALOG
    ]}


def merge_catalog(data):
    """Overlay persisted dates/focus on the canonical catalog.

    The catalog owns curriculum shape. The state file owns learner progress, so
    matching category/subpattern timestamps survive catalog expansion while
    removed curriculum entries disappear on the next sync.
    """

    merged = default_state()
    old_categories = {item.get("slug"): item for item in data.get("categories", [])}
    valid_categories = {item[0] for item in CATALOG}
    for category in merged["categories"]:
        old_category = old_categories.get(category["slug"], {})
        for key in ("started_at", "completed_at"):
            category[key] = old_category.get(key)
        old_subpatterns = {item.get("slug"): item for item in old_category.get("subpatterns", [])}
        for subpattern in category["subpatterns"]:
            old_subpattern = old_subpatterns.get(subpattern["slug"], {})
            for key in ("started_at", "completed_at"):
                subpattern[key] = old_subpattern.get(key)

    focus = data.get("current_focus")
    if isinstance(focus, dict) and focus.get("category") in valid_categories:
        merged["current_focus"] = focus
    return merged


def load_state(r):
    path = state_path(r)
    if not path.exists(): return default_state()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != VERSION: raise ValueError("unsupported pattern-sweep.json version")
    return merge_catalog(data)


def save_state(r, data):
    state_path(r).parent.mkdir(parents=True, exist_ok=True)
    state_path(r).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def notes(r):
    out = {}
    for path in r.glob("problems/*/*/note.md"):
        match = META_RE.search(path.read_text(encoding="utf-8"))
        if match:
            try: out[json.loads(match.group(1))["slug"]] = (path, json.loads(match.group(1)))
            except (json.JSONDecodeError, KeyError): pass
    return out


def complete(problem, indexed):
    found = indexed.get(problem["slug"])
    if not found: return False
    path, meta = found
    return meta.get("status") == "AC" and bool(meta.get("stats", {}).get("teach_back_done")) and (path.parent / "solution.py").is_file()


def progress(state, indexed):
    for cat in state["categories"]:
        for sub in cat["subpatterns"]:
            sub["completed"] = all(complete(p, indexed) for p in sub["problems"])
            sub["completed_count"] = sum(complete(p, indexed) for p in sub["problems"])
            sub["total_count"] = len(sub["problems"])
        cat["completed"] = all(s["completed"] for s in cat["subpatterns"])
        cat["completed_count"] = sum(s["completed_count"] for s in cat["subpatterns"])
        cat["total_count"] = sum(s["total_count"] for s in cat["subpatterns"])
    return state


def reconcile(state, indexed):
    progress(state, indexed)
    for cat in state["categories"]:
        for sub in cat["subpatterns"]:
            if sub["completed_count"] and not sub.get("started_at"): sub["started_at"] = date()
            if sub["completed"] and not sub.get("completed_at"): sub["completed_at"] = date()
            if not sub["completed"]: sub["completed_at"] = None
        if cat["completed_count"] and not cat.get("started_at"): cat["started_at"] = date()
        if cat["completed"]:
            latest_subpattern = max(sub["completed_at"] for sub in cat["subpatterns"])
            if not cat.get("completed_at") or cat["completed_at"] < latest_subpattern:
                cat["completed_at"] = latest_subpattern
        else:
            cat["completed_at"] = None
    return state


def render_map(cat, indexed):
    lines = [START, "", "## Sweep Map", "", "| Subpattern | Status | Representative problems |", "| --- | --- | --- |"]
    for sub in cat["subpatterns"]:
        problems = []
        for p in sub["problems"]:
            status = "complete" if complete(p, indexed) else "todo"
            problems.append(f"#{p['id']} {p['title']} ({status})")
        status = "complete" if sub["completed"] else f"{sub['completed_count']}/{sub['total_count']}"
        lines.append(f"| {sub['title']} | {status} | {'; '.join(problems)} |")
    lines += ["", END, ""]
    return "\n".join(lines)


def ensure_card(r, cat):
    path = pattern_path(r, cat)
    if path.exists(): return path
    template = (r / "templates" / "pattern-note.md").read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template.replace("<name>", cat["title"]), encoding="utf-8")
    return path


def sync_cards(r, state, indexed):
    for cat in state["categories"]:
        path = ensure_card(r, cat)
        text = path.read_text(encoding="utf-8").rstrip() + "\n"
        block = render_map(cat, indexed)
        if START in text and END in text:
            text = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", block, text, flags=re.S)
        else:
            text += "\n" + block
        path.write_text(text, encoding="utf-8")


def render_progress(state):
    completed = sum(category["completed_count"] for category in state["categories"])
    total = sum(category["total_count"] for category in state["categories"])
    lines = [
        "# Pattern Sweep Progress",
        "",
        "> 此文件由 `leetcode-coach sweep sync` 自动生成。权威进度源是",
        "> [`study/pattern-sweep.json`](../../study/pattern-sweep.json) 与各题 `note.md`；请勿手改本页状态。",
        "",
        f"总体进度：**{completed}/{total}** 道代表题完成。完成要求为 AC、存在归档解法且 Teach-back 完整。",
        "",
        "| Pattern | Progress | Status | Started | Completed |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for category in state["categories"]:
        status = "complete" if category["completed"] else ("in progress" if category["completed_count"] else "not started")
        lines.append(
            f"| [{category['title']}](./{category['pattern_file']}) | "
            f"{category['completed_count']}/{category['total_count']} | {status} | "
            f"{category.get('started_at') or '—'} | {category.get('completed_at') or '—'} |"
        )
    lines += ["", "## Subpattern Details", ""]
    for category in state["categories"]:
        lines += [f"### [{category['title']}](./{category['pattern_file']})", ""]
        for subpattern in category["subpatterns"]:
            marker = "x" if subpattern["completed"] else " "
            lines.append(
                f"- [{marker}] {subpattern['title']} — "
                f"{subpattern['completed_count']}/{subpattern['total_count']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sync_progress(r, state):
    progress_path(r).parent.mkdir(parents=True, exist_ok=True)
    progress_path(r).write_text(render_progress(state), encoding="utf-8")


def due(indexed):
    today = date()
    return sorted((m for _, m in indexed.values() if m.get("status") in {"AC", "Review"} and m.get("next_review") and m["next_review"] <= today), key=lambda m: (m["next_review"], m.get("id", 0)))


def next_item(state, indexed):
    reviews = due(indexed)
    if reviews: return {"kind": "due-review", "problem": reviews[0]}
    progress(state, indexed)
    category = next_category(state)
    if category:
        return next_in_category(category, indexed)
    return None


def next_category(state):
    """Keep the active category until complete, then prefer untouched work."""

    categories = state["categories"]
    focus_slug = (state.get("current_focus") or {}).get("category")
    focused = next((cat for cat in categories if cat["slug"] == focus_slug), None)
    if focused:
        if not focused["completed"]:
            return focused
        return next((cat for cat in categories if not cat.get("started_at") and not cat["completed"]), None) \
            or next((cat for cat in categories if not cat["completed"]), None)

    # Older state files may not have current_focus. Recover the most recently
    # started category; if it just completed, advance to untouched curriculum.
    # Catalog order is the deterministic tie-breaker for equal dates.
    started = [cat for cat in categories if cat.get("started_at")]
    if started:
        latest_started = max(cat["started_at"] for cat in started)
        recent = next(cat for cat in started if cat["started_at"] == latest_started)
        if not recent["completed"]:
            return recent
        return next((cat for cat in categories if not cat.get("started_at") and not cat["completed"]), None) \
            or next((cat for cat in categories if not cat["completed"]), None)

    return next((cat for cat in categories if not cat.get("started_at") and not cat["completed"]), None) \
        or next((cat for cat in categories if not cat["completed"]), None)


def next_in_category(cat, indexed):
    for sub in cat["subpatterns"]:
        if sub["completed_count"] == 0:
            return next_in_sub(cat, sub, indexed)
    for sub in cat["subpatterns"]:
        if not sub["completed"]:
            return next_in_sub(cat, sub, indexed)
    return None


def next_in_sub(cat, sub, indexed):
    for p in sub["problems"]:
        if not complete(p, indexed):
            return {"kind": "sweep", "category": cat, "subpattern": sub, "problem": p, "needs_mcp": p["slug"] not in indexed}
    return None


def command_bootstrap(args):
    r = root(args); state = reconcile(load_state(r), notes(r)); save_state(r, state); sync_cards(r, state, notes(r)); sync_progress(r, state); print(state_path(r)); return 0


def command_sync(args):
    r = root(args); indexed = notes(r); state = reconcile(load_state(r), indexed); save_state(r, state); sync_cards(r, state, indexed); sync_progress(r, state); print("Synced pattern sweep maps and progress mirror."); return 0


def command_status(args):
    r = root(args); state = progress(load_state(r), notes(r));
    for cat in state["categories"]:
        print(f"{cat['title']}: {cat['completed_count']}/{cat['total_count']} {'complete' if cat['completed'] else 'open'}")
        for sub in cat["subpatterns"]: print(f"  - {sub['title']}: {sub['completed_count']}/{sub['total_count']}")
    if state.get("current_focus"): print("Focus: " + json.dumps(state["current_focus"], ensure_ascii=False))
    return 0


def command_next(args):
    r = root(args); indexed = notes(r); state = load_state(r); item = next_item(state, indexed)
    if not item: print("Sweep complete."); return 0
    p = item["problem"]
    if item["kind"] == "due-review": print(f"Due review: #{p.get('id')} {p.get('title')} ({p.get('slug')})")
    else:
        print(f"Sweep: {item['category']['title']} / {item['subpattern']['title']}")
        print(f"Next: #{p['id']} {p['title']} [{p['difficulty']}] slug={p['slug']}")
        if item["needs_mcp"]: print("needs_mcp=true: fetch metadata before init-problem.")
    if args.set_focus:
        state["current_focus"] = {"category": item.get("category", {}).get("slug"), "subpattern": item.get("subpattern", {}).get("slug"), "problem_slug": p.get("slug"), "set_at": date()}
        save_state(r, state)
    return 0


def command_check(args):
    r = root(args); state = load_state(r); indexed = notes(r); errors = []; seen = set()
    if not progress_path(r).is_file():
        errors.append(f"missing generated progress mirror: {progress_path(r)}")
    for cat in state.get("categories", []):
        path = pattern_path(r, cat)
        if not path.exists(): errors.append(f"missing pattern card: {path}")
        elif START not in path.read_text(encoding="utf-8") or END not in path.read_text(encoding="utf-8"):
            errors.append(f"missing sweep map markers: {path}")
        live_cat_complete = True
        for sub in cat.get("subpatterns", []):
            live_sub_complete = True
            for p in sub.get("problems", []):
                slug = p.get("slug")
                if not slug: errors.append(f"missing slug in {cat.get('slug')}/{sub.get('slug')}"); continue
                if slug in seen: errors.append(f"duplicate representative slug: {slug}")
                seen.add(slug)
                found = indexed.get(slug)
                if found and found[1].get("id") != p.get("id"): errors.append(f"id mismatch for {slug}")
                live_sub_complete = live_sub_complete and complete(p, indexed)
            if sub.get("completed_at") and not live_sub_complete:
                errors.append(f"invalid completed_at for open subpattern: {cat.get('slug')}/{sub.get('slug')}")
            live_cat_complete = live_cat_complete and live_sub_complete
        if cat.get("completed_at") and not live_cat_complete:
            errors.append(f"invalid completed_at for open category: {cat.get('slug')}")
    if errors:
        print("\n".join(errors), file=sys.stderr); return 1
    print("Pattern sweep check passed."); return 0


def parser():
    p = argparse.ArgumentParser(); p.add_argument("--root"); sub = p.add_subparsers(required=True)
    for name, func in [("bootstrap", command_bootstrap), ("sync", command_sync), ("status", command_status), ("next", command_next), ("check", command_check)]:
        x = sub.add_parser(name); x.set_defaults(func=func)
        if name == "next": x.add_argument("--set-focus", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Error: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
