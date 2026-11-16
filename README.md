# ADBS Week 3 Storage Engine Lab

You will implement nine functions in `lab.py` across five tasks. The checker runs multiple cases for each task, including edge cases. Use Python 3.10 or later. Run these commands from this folder.

```sh
python -m pip install -r requirements.txt
python grade.py --task 1
python experiment.py --task 1
```

Replace `1` with the task number from `2` to `5`. The grader uses the standard library and reports unfinished functions as failures. Run `python grade.py` for all public checks. Run each experiment after its task passes. Submit **`lab.py` and the completed `Answer_Sheet.docx`**. The first three tasks use the supplied sales files. The last two use fixed trees from the lecture and run without PyArrow.

## Task 1 Plan a Parquet scan

Implement `plan_scan(groups, projection, filters)` in `lab.py`. The experiment converts Parquet metadata into the `RowGroup` and `Chunk` types in `models.py`. Work on that metadata. The planner does not need access to any row values.

- `groups` is in file order and group IDs are zero-based.
- `projection` lists output columns. Keep the first occurrence of each name and append any additional filter columns in dictionary order.
- Filters form a conjunction (AND). Each maps a column to an inclusive `(low, high)` interval. A `None` endpoint is unbounded. Bounds, when both present, have `low <= high`. All requested column names exist for each nonempty group.
- Skip empty groups. A nonempty group can be skipped if **any** filter interval is disjoint from a known bound. A maximum below the lower threshold or a minimum above the upper threshold proves disjointness. Equality at the boundary keeps the group. Use each known endpoint independently. Missing statistics alone cannot justify skipping a group.
- Return a `ScanPlan` with the retained group IDs, required columns, number of chunks and total compressed bytes. Read one chunk per required column in every retained group. Preserve the input.

For example, if group 0 has order IDs 1–10 and group 1 has IDs 11–20, a query for 10–11 retains both groups. If the query projects `amount`, the planner also counts the `order_id` chunks used to filter the rows.

Query A projects `amount` for order IDs 1950–2050. Query B projects `category` and `quantity` for order IDs 4001–4150 with `quantity >= 3`. Byte counts are compressed chunk sizes from metadata.

**Written results.** Record the group IDs and compressed bytes for the two queries in the experiment. For Query A, calculate the bytes skipped compared with reading the same required columns in all groups.

## Task 2 Build an adaptive integer page

Write `encode_page(values)` and `decode_page(frame)`. The encoder receives a list of **0 to 65,535** integers in **0 to 255**. It returns a `bytes` object in the smaller of two formats. Compare full frame lengths, including their headers. Choose `P` on a tie. Leave the input list intact.

| Mode | Header | Payload |
|---|---|---|
| `R` | ASCII `R` and a two-byte unsigned value count | One byte for the value and two bytes for the run length, for each maximal adjacent run |
| `P` | ASCII `P`, a two-byte unsigned value count and a one-byte bit width | Values in input order using exactly that many bits each |

Use **little-endian** for all two-byte fields. The packed width is `max(1, max(values, default=0).bit_length())`. Bits enter the payload from the least significant bit of the first byte toward higher bits and continue into the next byte. Pad unused high bits of the final byte with zeros. For example, values `[5, 2, 7]` use three bits each. Their packed payload is `d5 01` in hexadecimal. The empty input has no payload.

For decoding, handle both well-formed formats, including a valid frame that your encoder would have encoded using the other mode. Return the values in original order. Corrupt frames are outside this task.

The experiment encodes the `quantity` column for two layouts with 128 records per page. One keeps the CSV order. The other sorts complete rows by quantity, then by order ID. The first layout scans every page for `quantity = 3`. The sorted layout uses in-memory page min/max bounds to skip pages whose bounds exclude 3. Page reads are counts in this model.

**Written results.** Fill the single comparison table from the experiment.

## Task 3 Implement ISAM inserts and range scans

Implement `insert(index, key)` and `range_scan(index, low, high)`. The `ISAM` object has fixed, increasing separators and one primary page and overflow chain per partition. Every page holds at most `capacity` keys.

- A separator is the lower bound of the partition to its right. For separators `(20, 40)`, the partitions are `key < 20`, `20 <= key < 40` and `key >= 40`.
- Insert into the target primary page if it has space. When it is full, append to the last overflow page if that page has space, or append a new overflow page. Accept duplicate keys. Preserve insertion order within each page. Leave the separators and other partitions as they were. Return `(partition_id, page_number)`, where 0 denotes the primary page and 1 denotes the first overflow page.
- A range scan is inclusive. Raise `ValueError` for `low > high`. Visit only the partitions whose key intervals intersect the range, in partition order. Read the primary page first, then every overflow page in chain order. Count every visited page, including an empty primary page. An overflow page can contain keys in any order.
- Return a `RangeResult` with matching keys as a sorted tuple, retaining duplicates. Its `pages` tuple lists `(partition_id, page_number)` in exactly the order visited. Preserve the index during a scan.

Example. With separator 20, capacity 2, and primary pages `[[3, 5], [20, 23]]`, inserting 19 returns `(0, 1)`. A scan of `[19, 20]` reads `((0, 0), (0, 1), (1, 0))` and returns keys `(19, 20)`.

The ISAM experiment has separators 40 and 80, capacity 2 and initial pages `[[10, 20], [40, 50], [80, 90]]`. Insert 25, 37 and 35 in that order, then scan `[35, 40]`.

**Written results.** Record the page allocated for order 35, the matching keys and the total data pages read for `[35, 40]`. All model keys in the experiment come from the supplied CSV.

## Task 4 Search and insert in a B+ tree

Implement `bplus_range(tree, low, high)` and `bplus_insert(tree, key, strategy="split")`. The supplied `bplus.py` models the lecture tree with two to four keys per nonroot page. Each internal separator routes equality to the child on its right. Some separators are routing boundaries between actual leaf keys.

- For an **inclusive range**, use `find_leaf(tree, low)` once and follow the leaf `next` links. Return matching keys as a tuple in increasing order. Stop when a key exceeds `high`. Raise `ValueError` for reversed bounds. Do not modify the tree.
- Insert each new integer key into its leaf in sorted order. Return `False` for a duplicate, leaving the tree intact. Return `True` when a key is inserted. Reject an unknown strategy with `ValueError` before modifying the tree.
- In `"redistribute"` mode, try to move one key to a sibling of the same parent if a leaf overflows. Try the right sibling first, then the left. A sibling must have room for the key. Move the largest key right or the smallest key left, and update the separator between the two leaves to the first key of the right-hand leaf.
- In `"split"` mode, or if redistribution cannot help, split the five keys into two on the left and three on the right. Link the new right leaf after the old leaf. Copy the new right leaf’s first key into the parent. Use `link_after` and `insert_parent` for link maintenance and propagation. If an internal page overflows, the supplied `insert_parent` moves the middle separator up and removes it from the two resulting pages.

Run `python grade.py --task 4`, then `python experiment.py --task 4`. The experiment finds the leaf for key 20 and scans 19–29. On separate fresh trees, it inserts 15 without overflow, 6 with redistribution, and 8 with a split.

**Written results.** Record the leaf for 20 and the range matches (4.1), the leaf after inserting 15 and replacement separator after inserting 6 (4.2), and the copied-up key, pushed-up key and final leaf depth after inserting 8 (4.3). Depth counts edges from the root.

## Task 5 Delete from a B+ tree and estimate key capacity

Implement `bplus_delete(tree, key)` and `prefix_page_stats(keys, page_bytes, header_bytes, pointer_bytes, key_bytes_before, key_bytes_after)`.

- Delete the key from its leaf. An absent key returns `False` and leaves the tree intact. A successful deletion returns `True`. A nonroot leaf underflows with fewer than two keys. The root can be an empty leaf. If there is no underflow, leave separators in place as long as their routing boundaries still hold.
- When a leaf underflows, try to borrow first from the right sibling and then from the left. Both must share the parent, and a donor must have more than two keys. Move the smallest key from the right sibling or the largest key from the left. Update the separator between them to the first key of the right-hand leaf.
- If borrowing fails, merge with the right sibling when it exists, otherwise merge into the left. Keep keys sorted. Unlink the removed leaf and remove its child pointer and adjacent separator from the parent. Call the supplied `repair_internal(tree, parent)` to handle any cascading underflow and root shrink.
- For the key estimate, find the longest shared prefix of the input strings, using whole characters. Count raw UTF-8 bytes, then count the UTF-8 bytes of one prefix plus every suffix. Ignore compression metadata. The empty list stores zero bytes. Entries per page before and after are the integer part of usable bytes divided by pointer bytes plus the corresponding average key length. Usable bytes are page bytes minus header bytes. Assume a nonnegative usable size and a positive pointer size. Return a tuple of raw bytes, compressed bytes, entries before and entries after, in that order.

Run `python grade.py --task 5`, then `python experiment.py --task 5`. The deletion fixture starts from the lecture’s post-insertion tree and runs independently of your Task 4 code. It deletes 19, then 20, then 24. The size example uses `robbed`, `robbing` and `robot`, a 128-byte page, a 16-byte header and an 8-byte pointer. The average key lengths are 12 and 4 bytes.

**Written results.** Record the receiver leaf and replacement separator after borrowing (5.1), the merged leaf, final root and depth after the cascade (5.2), and the byte totals and two capacity estimates (5.3).
