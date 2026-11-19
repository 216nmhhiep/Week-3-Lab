# Week 3 Storage Engine Lab

**Submit your completed [lab.py](lab.py) with all nine functions implemented and [Answer_Sheet.docx](Answer_Sheet.docx) with all five task sections filled in.**

In this lab, you will build parts of a small storage engine: a Parquet scan planner, an integer page codec, an ISAM index and B+ tree operations. You will write Python code, check it against multiple tests, then run fixed experiments and record the results.

There are **five tasks and nine functions to implement** in [lab.py](lab.py). The data, helper classes, tests and experiment scripts are provided.

## Learning objectives

By the end of this lab, students will be able to:

- **Apply Parquet metadata** to select the row groups and columns a query needs, and calculate compressed bytes read.
- **Write lossless RLE and bit-packing codecs** and compare compression and page reads for different file layouts.
- **Implement ISAM insertion and range scans**, including overflow pages, and count page accesses.
- **Implement B+ tree range search and insertion**, using leaf links, redistribution and splits.
- **Implement B+ tree deletion** with borrowing and merging, and calculate how prefix compression affects page capacity.

## 1. Set up your workspace

Use **Python 3.10 or later**. Open a terminal in this `student` folder and install the dependency:

```sh
python -m pip install -r requirements.txt
```

Keep the supplied folder structure so the scripts can locate the data and helper modules.

| File or folder | What you use it for |
|---|---|
| [lab.py](lab.py) | Replace the nine `NotImplementedError` placeholders with your code. |
| [TASKS.md](TASKS.md) | Read the exact input/output rules, encoding format and tree policies. |
| [models.py](models.py), [bplus.py](bplus.py) | Use the provided data structures and tree helpers. |
| [grade.py](grade.py), [bplus_checks.py](bplus_checks.py) | Run and inspect the public tests. |
| [experiment.py](experiment.py), [bplus_experiments.py](bplus_experiments.py) | Run the fixed experiments after implementing each task. |
| `data/` | Use the supplied sales CSV and Parquet files. |
| [Answer_Sheet.docx](Answer_Sheet.docx) | Fill in the requested experiment results. |

Tasks 1–3 reuse the supplied sales data. Tasks 4–5 use fixed trees from the lecture. Each task can be tested independently; Task 5 has its own starting tree and does not require your Task 4 insertion code.

## 2. Complete the five tasks

Use the descriptions below to understand the work. Before coding each task, read its linked specification for the precise rules the tests expect. Keep the supplied function names, parameters and return types.

### Task 1 — Plan a Parquet scan

**Implement:** `plan_scan(groups, projection, filters)`.

Use Parquet metadata to produce a `ScanPlan` describing the row groups, columns and compressed bytes required by a query. Your implementation should work for different projections and filters.

**Record:** Retained group IDs and compressed bytes for both experiment queries, plus the bytes skipped for Query A.

[Task 1 requirements](TASKS.md#task-1-plan-a-parquet-scan)

### Task 2 — Compare compression and file layouts

**Implement:** `encode_page(values)` and `decode_page(frame)`.

Build a lossless integer page codec supporting run-length encoding and bit packing. Use the experiment to compare storage size and page reads for the original and sorted sales layouts.

**Record:** Fill in **one comparison table** with total frame bytes, `R` pages, `P` pages and page reads for each layout.

[Task 2 requirements](TASKS.md#task-2-build-an-adaptive-integer-page)

### Task 3 — Insert and search in ISAM

**Implement:** `insert(index, key)` and `range_scan(index, low, high)`.

Support insertion and inclusive range queries on the supplied ISAM model. Report both query matches and page accesses, including the effects of overflow pages.

**Record:** The receiving page for order 35, the keys matching the experiment's range query and the total data pages read.

[Task 3 requirements](TASKS.md#task-3-implement-isam-inserts-and-range-scans)

### Task 4 — Search and insert in a B+ tree

**Implement:** `bplus_range(tree, low, high)` and `bplus_insert(tree, key, strategy="split")`.

Support inclusive range queries and insertion on the supplied B+ tree model. The resulting tree must satisfy the specified structure and insertion policy.

**Record:** Search results, requested leaf contents, separator changes, copied-up and pushed-up keys, and final leaf depth from the experiment.

[Task 4 requirements](TASKS.md#task-4-search-and-insert-in-a-b-tree)

### Task 5 — Delete from a B+ tree and estimate capacity

**Implement:** `bplus_delete(tree, key)` and `prefix_page_stats(...)`.

Support deletion while preserving a valid B+ tree. Calculate string-storage bytes and estimated page capacity before and after prefix compression.

**Record:** Requested leaf and separator changes, final root and leaf depth, raw and compressed key bytes, and both page capacities.

[Task 5 requirements](TASKS.md#task-5-delete-from-a-b-tree-and-estimate-key-capacity)

## 3. Test your code and fill in the answer sheet

For each task, write the code, run its tests, fix failures, then run its experiment. For Task 1:

```sh
python grade.py --task 1
python experiment.py --task 1
```

Replace `1` with `2`, `3`, `4` or `5` for the other tasks. A successful test run ends with `OK`. If a test fails, read its name and the expected/actual values or traceback to identify the rule your implementation missed. Unfinished functions report `NotImplementedError`.

The tests include edge cases beyond the experiment examples. Implement the general rules rather than hard-coding the printed results. You can inspect and run all **42 public tests** yourself:

```sh
python grade.py
```

Copy the requested experiment values into the matching sections of `Answer_Sheet.docx`. Use the supplied data and fixtures: these results are fixed, and page reads are counts in the model. Execution time is not an answer to any question.
