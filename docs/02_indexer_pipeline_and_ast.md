# 🔄 Python Indexer Pipeline & AST Deep Dive

This document details the internal mechanisms of the **Python Indexer Pipeline**, explaining how source code is transformed from raw text into an intelligent, queryable dependency graph through Python's Abstract Syntax Tree (`ast`).

---

## 1. The 5-Step Indexing Pipeline

```mermaid
flowchart TD
    subgraph Step1 ["Step 1: Scan & Hash"]
        S1["File Discovery\n(Filter .py, exclude .venv/.git)"] --> H1["Compute SHA-256 Hashes"]
        H1 --> D1{"Changed vs\nPrevious Run?"}
    end

    subgraph Step2 ["Step 2: AST Parsing"]
        AST["ast.parse(source_code)"]
        V1["SymbolVisitor\n(Classes, Functions, Signatures)"]
        V2["ImportVisitor\n(Imports, From-Imports, Aliases)"]
        V3["CallVisitor\n(Function Calls, Attribute Lookups)"]
        V4["Hierarchy Visitor\n(Inheritance Bases)"]
    end

    subgraph Step3 ["Step 3: Symbol Resolution"]
        R1["Build Global Symbol Lookup Tables"]
        R2["Resolve Imports & Aliases"]
        R3["Resolve Bound Methods (self/cls)"]
        R4["Assign target_symbol_id to References"]
    end

    subgraph Step4 ["Step 4: Graph Construction"]
        G1["Add Module & Symbol Nodes"]
        G2["Add 'defines' Edges"]
        G3["Add 'imports' Edges"]
        G4["Add 'call' & 'attribute' Edges"]
    end

    subgraph Step5 ["Step 5: Persistence"]
        DB1[("SQLite Database\n(Atomic Transaction)")]
        DB2[("Neo4j Property Graph\n(Optional Driver)")]
    end

    D1 -- "Identical (0 changes)" --> SKIP["Return cached summary (Skip)"]
    D1 -- "Modified / New" --> AST
    AST --> V1 & V2 & V3 & V4
    V1 & V2 & V3 & V4 --> R1
    R1 --> R2 --> R3 --> R4
    R4 --> G1 --> G2 --> G3 --> G4
    G4 --> DB1 & DB2
```

---

## 2. Step-by-Step Execution Details

### Step 1: Scan & Hash Validation
- Discovers all `.py` files recursively using `Path.rglob("*")`.
- Filters out non-source directories using exclusion patterns: `.git`, `__pycache__`, `.venv`, `venv`, `node_modules`, `.pytest_cache`, `.eggs`, `build`, `dist`.
- Computes chunked **SHA-256 digests** of file contents.
- Compares against previous hashes stored in SQLite. If all hashes match and the repository exists, indexing completes instantaneously without re-parsing.

### Step 2: AST Parsing (`analyzers/python/`)
For each changed file, the source code is parsed into an AST tree using Python's built-in `ast.parse(source, filename=path)`:
1. **Module ID Generation**: Converts relative file paths into dotted module names:
   - `api/routes/matches.py` $\rightarrow$ `api.routes.matches`
   - `matching/__init__.py` $\rightarrow$ `matching`
2. **`SymbolVisitor`** (`ast.NodeVisitor`):
   - Traverses `ClassDef`, `FunctionDef`, `AsyncFunctionDef`, `Assign`, `AnnAssign`.
   - Maintains a `scope_stack` to produce nested qualified names (e.g. `MyClass.my_method`).
   - Uses `ast.unparse(node.args)` to construct readable parameter signatures.
3. **`ImportVisitor`**:
   - Records standard `import foo.bar as baz` (`ast.Import`).
   - Records from-imports `from foo import bar as baz` (`ast.ImportFrom`), computing relative levels (`.` vs `..`).
4. **`CallVisitor`**:
   - Tracks the active enclosing symbol via line-number scoped lookup (`scopes`).
   - Extracts invocation targets from `ast.Call` (e.g., `calculate_total(...)` or `self.service.process(...)`).
   - Extracts dotted attribute accesses from `ast.Attribute`.
5. **Class Hierarchy Walk**:
   - Extracts base class identifiers (`ast.Name` and `ast.Attribute`) to model inheritance.

### Step 3: Symbol Resolution (`core/resolver.py`)
Raw call sites and attribute accesses only contain text strings (e.g., `"get_user"` or `"self.repo.find"`). The **Symbol Resolver** matches these strings to unambiguous global symbol IDs (`module:qualified_name`):

```
Resolution Priority:
1. Direct Symbol ID Match (target_name exists in global symbol table)
2. Bound Method Resolution:
   - If target starts with 'self.' or 'cls.', inspect the enclosing class.
   - Traverse the class inheritance hierarchy to find inherited methods.
3. Import Alias Dereferencing:
   - If target starts with an alias ('np.mean'), map 'np' -> 'numpy' and resolve.
4. Single Local Candidate (unambiguous unqualified match across repository).
5. Same-Module Priority (symbol with matching name declared in the caller's module).
```

### Step 4: Graph Construction (`core/graph.py`)
Transforms resolved symbols and references into a directed graph (`NetworkX.DiGraph`):
- **Nodes**:
  - Module nodes: `api.routes.matches:<module>`
  - Symbol nodes: `api.routes.matches:get_user_matches`
- **Edges & Relationships**:
  - `defines`: Connects module $\rightarrow$ symbols defined within it.
  - `imports`: Connects module $\rightarrow$ imported target modules.
  - `call`: Connects caller symbol $\rightarrow$ callee symbol.
  - `attribute`: Connects source symbol $\rightarrow$ accessed symbol/field.

### Step 5: Persistence (`storage/`)
- Saves records into SQLite within an atomic `with connection:` block.
- Pushes property graph nodes and edges to Neo4j if configured.

---

## 3. Concrete Example: From Python Code to AST & Graph

To see the indexer in action, consider this simple service file `services/order.py`:

```python
# services/order.py
from db.client import DatabaseClient

class OrderService:
    def __init__(self):
        self.db = DatabaseClient()

    def process_order(self, order_id: str) -> bool:
        return self.db.save(order_id)
```

---

### 3.1. What the Python AST Looks Like

When `ast.parse()` parses `process_order`, Python generates an AST tree equivalent to:

```text
FunctionDef(
    name='process_order',
    args=arguments(
        args=[
            arg(arg='self'),
            arg(arg='order_id', annotation=Name(id='str'))
        ]
    ),
    returns=Name(id='bool'),
    body=[
        Return(
            value=Call(
                func=Attribute(
                    value=Attribute(
                        value=Name(id='self'),
                        attr='db'
                    ),
                    attr='save'
                ),
                args=[Name(id='order_id')]
            )
        )
    ],
    lineno=8,
    end_lineno=9
)
```

---

### 3.2. AST Visitors in Action

```mermaid
graph TD
    AST_ROOT["Module: services/order.py"]
    
    IMP_NODE["ast.ImportFrom\nmodule='db.client', name='DatabaseClient'"]
    CLASS_NODE["ast.ClassDef\nname='OrderService'"]
    INIT_NODE["ast.FunctionDef\nname='__init__'"]
    FUNC_NODE["ast.FunctionDef\nname='process_order'"]
    CALL_NODE["ast.Call\nfunc='self.db.save'"]

    AST_ROOT --> IMP_NODE
    AST_ROOT --> CLASS_NODE
    CLASS_NODE --> INIT_NODE
    CLASS_NODE --> FUNC_NODE
    FUNC_NODE --> CALL_NODE

    IMP_NODE -.->|ImportVisitor| OUT_IMP["Import Record:\nlocal_name='DatabaseClient'\nimported_path='db.client.DatabaseClient'"]
    CLASS_NODE -.->|SymbolVisitor| OUT_CLS["Symbol: services.order:OrderService"]
    INIT_NODE -.->|SymbolVisitor| OUT_INIT["Symbol: services.order:OrderService.__init__"]
    FUNC_NODE -.->|SymbolVisitor| OUT_FUNC["Symbol: services.order:OrderService.process_order"]
    CALL_NODE -.->|CallVisitor| OUT_REF["Reference:\nsource='services.order:OrderService.process_order'\ntarget_name='self.db.save'\nstatus='unresolved'"]
```

---

### 3.3. Resolver Step (Connecting References to Target IDs)

The `SymbolResolver` evaluates `OUT_REF`:
1. Source symbol: `services.order:OrderService.process_order`
2. Target name: `self.db.save`
3. Lookup discovers `DatabaseClient.save` in `db.client`.
4. Status transitions from `unresolved` $\rightarrow$ `resolved`:
   - `target_symbol_id` = `"db.client:DatabaseClient.save"`
   - `resolution_status` = `ResolutionStatus.RESOLVED`

---

### 3.4. Final Generated Graph Edges

The graph builder turns this into directed edges:

```mermaid
graph LR
    MOD["services.order:<module>"]
    CLS["services.order:OrderService"]
    INIT["services.order:OrderService.__init__"]
    PROC["services.order:OrderService.process_order"]
    DB_MOD["db.client:<module>"]
    DB_CLS["db.client:DatabaseClient"]
    DB_SAVE["db.client:DatabaseClient.save"]

    MOD -->|defines| CLS
    MOD -->|defines| INIT
    MOD -->|defines| PROC
    MOD -->|imports| DB_MOD
    INIT -->|call| DB_CLS
    PROC -->|call| DB_SAVE
```

This graph enables multi-hop queries like:
> *"If `DatabaseClient.save` is modified, what methods are directly impacted?"*  
> Tracing backwards from `DB_SAVE` instantly returns `services.order:OrderService.process_order`.
