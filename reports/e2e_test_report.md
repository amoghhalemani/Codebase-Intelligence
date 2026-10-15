# 🧪 Codebase Intelligence — End-to-End Test Execution Report

**Execution Timestamp:** `2026-10-15 10:52:58 UTC`  
**Total Suite Duration:** `210.44 ms`  
**Overall Status:** `✅ ALL PASSED`

---

## 📊 Executive Summary

| Total Use Cases | Passed | Failed | Pass Rate | Total Duration |
| :---: | :---: | :---: | :---: | :---: |
| **8** | **8** | **0** | **100.0%** | **210.44 ms** |

---

## 📋 Detailed Use Case Results

| # | Use Case Name | Category | Status | Duration | Summary |
| :--- | :--- | :--- | :---: | :---: | :--- |
| 1 | **1. Clean Repository Indexing** | `Indexing` | ✅ PASS | `77.45 ms` | Indexed 5 files, 14 symbols, 23 edges |
| 2 | **2. Incremental Indexing & Hash Cache** | `Indexing` | ✅ PASS | `61.04 ms` | Zero changes detected on unchanged run; exact modified file detected on edit |
| 3 | **3. Symbol Search & Detail Navigation** | `Navigation` | ✅ PASS | `2.24 ms` | Found symbol 'tax:calculate_vat' with 2 incoming caller(s) |
| 4 | **4. Graph Path & Call-Chain Query** | `Graph Traversal` | ✅ PASS | `3.91 ms` | Discovered call chain from 'orders:OrderService.place_order' to 'tax:calculate_vat' (length 3) |
| 5 | **5. Multi-Hop Impact Analysis** | `Impact Analysis` | ✅ PASS | `0.94 ms` | Calculated blast radius: 7 symbols impacted across 0 path(s) |
| 6 | **6. Impact-Driven Test Selection** | `Test Selection` | ✅ PASS | `2.69 ms` | Recommended 1 relevant test case(s) for changed symbol |
| 7 | **7. Dead Code Detection** | `Quality & Hygiene` | ✅ PASS | `6.01 ms` | Detected 4 unreferenced symbol finding(s); successfully flagged orphaned_dead_function |
| 8 | **8. Change Risk Scoring** | `Risk Assessment` | ✅ PASS | `5.98 ms` | Risk assessment: score 0.177/100, level: low |

---

## 🔍 Deep Dive by Query & Use Case

### 1. Clean Repository Indexing
- **Category:** `Indexing`
- **Status:** `PASS`
- **Execution Time:** `77.45 ms`
- **Summary:** Indexed 5 files, 14 symbols, 23 edges

```json
{
  "files_indexed": 5,
  "symbols_indexed": 14,
  "graph_nodes": 23,
  "graph_edges": 23
}
```

### 2. Incremental Indexing & Hash Cache
- **Category:** `Indexing`
- **Status:** `PASS`
- **Execution Time:** `61.04 ms`
- **Summary:** Zero changes detected on unchanged run; exact modified file detected on edit

```json
{
  "unchanged_run_updated": false,
  "modified_run_changed_files": [
    "tax.py"
  ]
}
```

### 3. Symbol Search & Detail Navigation
- **Category:** `Navigation`
- **Status:** `PASS`
- **Execution Time:** `2.24 ms`
- **Summary:** Found symbol 'tax:calculate_vat' with 2 incoming caller(s)

```json
{
  "symbol_id": "tax:calculate_vat",
  "kind": "function",
  "signature": "def calculate_vat(amount: float)",
  "callers": [
    "billing:prepare_invoice",
    "tax:<module>"
  ]
}
```

### 4. Graph Path & Call-Chain Query
- **Category:** `Graph Traversal`
- **Status:** `PASS`
- **Execution Time:** `3.91 ms`
- **Summary:** Discovered call chain from 'orders:OrderService.place_order' to 'tax:calculate_vat' (length 3)

```json
{
  "source": "orders:OrderService.place_order",
  "target": "tax:calculate_vat",
  "shortest_path": [
    "orders:OrderService.place_order",
    "billing:prepare_invoice",
    "tax:calculate_vat"
  ],
  "neighbors_of_billing": [
    "tax:calculate_discount",
    "tax:calculate_vat"
  ]
}
```

### 5. Multi-Hop Impact Analysis
- **Category:** `Impact Analysis`
- **Status:** `PASS`
- **Execution Time:** `0.94 ms`
- **Summary:** Calculated blast radius: 7 symbols impacted across 0 path(s)

```json
{
  "changed_symbol": "tax:calculate_vat",
  "impacted_symbols": [
    "billing:<module>",
    "billing:prepare_invoice",
    "orders:<module>",
    "orders:OrderService.place_order",
    "tax:<module>",
    "tests.test_billing:<module>",
    "tests.test_billing:test_prepare_invoice"
  ],
  "impact_paths": []
}
```

### 6. Impact-Driven Test Selection
- **Category:** `Test Selection`
- **Status:** `PASS`
- **Execution Time:** `2.69 ms`
- **Summary:** Recommended 1 relevant test case(s) for changed symbol

```json
{
  "changed_symbols": [
    "tax:calculate_vat"
  ],
  "recommended_test_files": [
    "tests/test_billing.py"
  ],
  "recommended_test_names": [
    "test_prepare_invoice"
  ]
}
```

### 7. Dead Code Detection
- **Category:** `Quality & Hygiene`
- **Status:** `PASS`
- **Execution Time:** `6.01 ms`
- **Summary:** Detected 4 unreferenced symbol finding(s); successfully flagged orphaned_dead_function

```json
{
  "total_findings": 4,
  "flagged_symbols": [
    "orders:OrderService",
    "utils:get_platform_info",
    "utils:orphaned_dead_function",
    "orders:OrderService.place_order"
  ]
}
```

### 8. Change Risk Scoring
- **Category:** `Risk Assessment`
- **Status:** `PASS`
- **Execution Time:** `5.98 ms`
- **Summary:** Risk assessment: score 0.177/100, level: low

```json
{
  "risk_score": 0.177,
  "risk_level": "low",
  "factors": {}
}
```
