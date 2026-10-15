"""JavaScript and TypeScript analyzer for Codebase Intelligence.

Parses JavaScript (ES6+, CommonJS, JSX) and TypeScript (TS, TSX) source files
using Tree-Sitter to extract symbols, classes, methods, imports, and call sites.
"""

from pathlib import Path
from typing import Any, Optional

import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tst
from tree_sitter import Language, Node, Parser

from analyzers.base import BaseAnalyzer
from core.models import Import, ParsedFile, Reference, Symbol


class JavaScriptAnalyzer(BaseAnalyzer):
    """AST analyzer for JavaScript and TypeScript files using Tree-Sitter."""

    language: str = "javascript"

    SUPPORTED_EXTENSIONS = {
        ".js": "js",
        ".mjs": "js",
        ".cjs": "js",
        ".jsx": "js",
        ".ts": "ts",
        ".tsx": "tsx",
    }

    def __init__(self) -> None:
        # Cache compiled Language and Parser instances
        self._js_lang = Language(tsjs.language())
        self._ts_lang = Language(tst.language_typescript())
        self._tsx_lang = Language(tst.language_tsx())

        self._js_parser = Parser(self._js_lang)
        self._ts_parser = Parser(self._ts_lang)
        self._tsx_parser = Parser(self._tsx_lang)

    def supports_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _get_parser_and_kind(self, path: Path) -> tuple[Parser, str]:
        ext = path.suffix.lower()
        if ext in (".ts",):
            return self._ts_parser, "typescript"
        if ext in (".tsx",):
            return self._tsx_parser, "typescript"
        return self._js_parser, "javascript"

    def parse_file(self, path: Path, repo_root: Path) -> ParsedFile:
        relative_path = path.relative_to(repo_root).as_posix()
        module_id = self._module_id(relative_path)
        parser, detected_lang = self._get_parser_and_kind(path)

        source_bytes = path.read_bytes()
        tree = parser.parse(source_bytes)

        symbols: list[Symbol] = []
        imports: list[Import] = []
        references: list[Reference] = []
        class_hierarchy: dict[str, list[str]] = {}

        # Traversal state
        scope_stack: list[str] = [f"{module_id}:<module>"]
        current_class: Optional[str] = None

        def node_text(node: Optional[Node]) -> str:
            if not node:
                return ""
            return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace").strip()

        def get_line_span(node: Node) -> tuple[int, int]:
            # Tree-sitter point is 0-indexed; convert to 1-indexed line numbers
            return node.start_point.row + 1, node.end_point.row + 1

        def normalize_import_module(raw_target: str) -> str:
            clean = raw_target.strip("'\"`")
            if clean.startswith("."):
                # Relative import: resolve relative to file directory
                file_dir = Path(relative_path).parent
                resolved = (file_dir / clean).resolve()
                # Normalize relative to repo root representation
                try:
                    rel = (Path(file_dir) / clean).as_posix()
                    # Clean up ./ and ../
                    import posixpath
                    normalized = posixpath.normpath(posixpath.join(file_dir.as_posix(), clean))
                    for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                        if normalized.endswith(ext):
                            normalized = normalized[: -len(ext)]
                    return normalized.replace("/", ".")
                except Exception:
                    return clean.replace("/", ".")
            return clean.replace("/", ".")

        def record_import(raw_module: str, imported_name: str, local_name: str, line_no: int, aliased: bool = False):
            mod_target = normalize_import_module(raw_module)
            full_imported_path = f"{mod_target}.{imported_name}" if imported_name and imported_name != "*" else mod_target
            imports.append(
                Import(
                    module=module_id,
                    file=relative_path,
                    imported_path=full_imported_path,
                    local_name=local_name or imported_name,
                    alias=local_name if aliased else None,
                    level=0,
                    line=line_no,
                )
            )
            references.append(
                Reference(
                    source_symbol_id=f"{module_id}:<module>",
                    target_name=full_imported_path,
                    target_symbol_id=None,
                    reference_type="import",
                    resolution_status="unresolved",
                    file=relative_path,
                    line=line_no,
                )
            )

        def record_call(call_name: str, line_no: int):
            if not call_name:
                return
            references.append(
                Reference(
                    source_symbol_id=scope_stack[-1],
                    target_name=call_name,
                    target_symbol_id=None,
                    reference_type="call",
                    resolution_status="unresolved",
                    file=relative_path,
                    line=line_no,
                )
            )

        def extract_call_name(node: Node) -> str:
            if node.type == "identifier":
                return node_text(node)
            if node.type == "member_expression":
                obj = node.child_by_field_name("object")
                prop = node.child_by_field_name("property")
                obj_name = extract_call_name(obj) if obj else ""
                prop_name = node_text(prop) if prop else ""
                if obj_name and prop_name:
                    return f"{obj_name}.{prop_name}"
                return prop_name or obj_name
            return node_text(node)

        def walk(node: Node):
            nonlocal current_class

            # -------------------------------------------------------------
            # 1. Function Declarations (function foo() {})
            # -------------------------------------------------------------
            if node.type in ("function_declaration", "generator_function_declaration"):
                name_node = node.child_by_field_name("name")
                name = node_text(name_node)
                if name:
                    start_line, end_line = get_line_span(node)
                    params_node = node.child_by_field_name("parameters")
                    params_text = node_text(params_node) if params_node else "()"
                    signature = f"function {name}{params_text}"

                    sym_id = f"{module_id}:{name}"
                    symbols.append(
                        Symbol(
                            id=sym_id,
                            name=name,
                            qualified_name=name,
                            kind="function",
                            file=relative_path,
                            module=module_id,
                            start_line=start_line,
                            end_line=end_line,
                            signature=signature,
                        )
                    )
                    scope_stack.append(sym_id)
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            walk(child)
                    scope_stack.pop()
                    return

            # -------------------------------------------------------------
            # 2. Variable Declarations (const foo = () => {}, const bar = require('./x'))
            # -------------------------------------------------------------
            if node.type in ("variable_declarator",):
                name_node = node.child_by_field_name("name")
                value_node = node.child_by_field_name("value")

                if name_node and value_node:
                    # Arrow function or anonymous function expression: const myFunc = (x) => ...
                    if value_node.type in ("arrow_function", "function_expression"):
                        name = node_text(name_node)
                        if name:
                            start_line, end_line = get_line_span(node)
                            params_node = value_node.child_by_field_name("parameters")
                            params_text = node_text(params_node) if params_node else "()"
                            sig_arrow = "=>" if value_node.type == "arrow_function" else ""
                            signature = f"const {name} = {params_text} {sig_arrow}".strip()

                            sym_id = f"{module_id}:{name}"
                            symbols.append(
                                Symbol(
                                    id=sym_id,
                                    name=name,
                                    qualified_name=name,
                                    kind="function",
                                    file=relative_path,
                                    module=module_id,
                                    start_line=start_line,
                                    end_line=end_line,
                                    signature=signature,
                                )
                            )
                            scope_stack.append(sym_id)
                            body = value_node.child_by_field_name("body")
                            if body:
                                for child in body.children:
                                    walk(child)
                            scope_stack.pop()
                            return

                    # CommonJS require: const { add } = require('./math') OR const math = require('./math')
                    elif value_node.type == "call_expression":
                        func_node = value_node.child_by_field_name("function")
                        args_node = value_node.child_by_field_name("arguments")
                        if func_node and node_text(func_node) == "require" and args_node and args_node.named_children:
                            raw_mod = node_text(args_node.named_children[0])
                            line_no = value_node.start_point.row + 1
                            if name_node.type == "object_pattern":
                                for prop in name_node.named_children:
                                    shorthand_name = node_text(prop)
                                    record_import(raw_mod, shorthand_name, shorthand_name, line_no)
                            else:
                                local_name = node_text(name_node)
                                record_import(raw_mod, local_name, local_name, line_no)

            # -------------------------------------------------------------
            # 3. Class Declarations (class UserService extends BaseService {})
            # -------------------------------------------------------------
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = node_text(name_node)
                if name:
                    start_line, end_line = get_line_span(node)
                    sym_id = f"{module_id}:{name}"

                    # Base class / inheritance
                    bases: list[str] = []
                    for child in node.children:
                        if child.type in ("class_heritage",):
                            for sub in child.children:
                                if sub.type in ("identifier", "type_identifier", "member_expression"):
                                    bases.append(node_text(sub))

                    class_hierarchy[sym_id] = bases

                    symbols.append(
                        Symbol(
                            id=sym_id,
                            name=name,
                            qualified_name=name,
                            kind="class",
                            file=relative_path,
                            module=module_id,
                            start_line=start_line,
                            end_line=end_line,
                            signature=f"class {name}",
                        )
                    )

                    prev_class = current_class
                    current_class = name
                    scope_stack.append(sym_id)

                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            walk(child)

                    scope_stack.pop()
                    current_class = prev_class
                    return

            # -------------------------------------------------------------
            # 4. Method Definitions (getUser(id) { ... })
            # -------------------------------------------------------------
            if node.type in ("method_definition",):
                name_node = node.child_by_field_name("name")
                name = node_text(name_node)
                if name:
                    start_line, end_line = get_line_span(node)
                    params_node = node.child_by_field_name("parameters")
                    params_text = node_text(params_node) if params_node else "()"

                    qualified_name = f"{current_class}.{name}" if current_class else name
                    sym_id = f"{module_id}:{qualified_name}"
                    signature = f"{qualified_name}{params_text}"

                    symbols.append(
                        Symbol(
                            id=sym_id,
                            name=name,
                            qualified_name=qualified_name,
                            kind="method",
                            file=relative_path,
                            module=module_id,
                            start_line=start_line,
                            end_line=end_line,
                            signature=signature,
                        )
                    )

                    scope_stack.append(sym_id)
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            walk(child)
                    scope_stack.pop()
                    return

            # -------------------------------------------------------------
            # 5. TypeScript Interfaces & Types
            # -------------------------------------------------------------
            if node.type in ("interface_declaration", "type_alias_declaration"):
                name_node = node.child_by_field_name("name")
                name = node_text(name_node)
                if name:
                    start_line, end_line = get_line_span(node)
                    kind = "interface" if node.type == "interface_declaration" else "type"
                    symbols.append(
                        Symbol(
                            id=f"{module_id}:{name}",
                            name=name,
                            qualified_name=name,
                            kind=kind,
                            file=relative_path,
                            module=module_id,
                            start_line=start_line,
                            end_line=end_line,
                            signature=f"{kind} {name}",
                        )
                    )

            # -------------------------------------------------------------
            # 6. ESM Imports (import { a, b as c } from './math')
            # -------------------------------------------------------------
            if node.type == "import_statement":
                source_node = node.child_by_field_name("source")
                raw_source = node_text(source_node)
                line_no = node.start_point.row + 1

                for child in node.children:
                    if child.type == "import_clause":
                        for clause_child in child.children:
                            # Default import: import express from 'express'
                            if clause_child.type == "identifier":
                                local_name = node_text(clause_child)
                                record_import(raw_source, local_name, local_name, line_no)
                            # Named imports: import { add, sub as subtract } from './math'
                            elif clause_child.type == "named_imports":
                                for spec in clause_child.children:
                                    if spec.type == "import_specifier":
                                        imported_node = spec.child_by_field_name("name")
                                        alias_node = spec.child_by_field_name("alias")
                                        imp_name = node_text(imported_node)
                                        loc_name = node_text(alias_node) if alias_node else imp_name
                                        record_import(raw_source, imp_name, loc_name, line_no, aliased=alias_node is not None)
                            # Namespace import: import * as math from './math'
                            elif clause_child.type == "namespace_import":
                                for sub in clause_child.children:
                                    if sub.type == "identifier":
                                        local_name = node_text(sub)
                                        record_import(raw_source, "*", local_name, line_no)

            # -------------------------------------------------------------
            # 7. Function Call Sites & Constructor Calls
            # -------------------------------------------------------------
            if node.type == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node:
                    call_name = extract_call_name(func_node)
                    # Ignore pure require calls which were handled under imports
                    if call_name != "require":
                        record_call(call_name, node.start_point.row + 1)

            elif node.type == "new_expression":
                ctor_node = node.child_by_field_name("constructor")
                if ctor_node:
                    ctor_name = extract_call_name(ctor_node)
                    record_call(ctor_name, node.start_point.row + 1)

            # Recurse children
            for child in node.children:
                walk(child)

        walk(tree.root_node)

        return ParsedFile(
            path=relative_path,
            module_id=module_id,
            language=detected_lang,
            symbols=symbols,
            imports=imports,
            references=references,
            class_hierarchy=class_hierarchy,
        )

    @staticmethod
    def _module_id(relative_path: str) -> str:
        # Strip all known JS/TS extensions
        without_extension = relative_path
        for ext in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
            if without_extension.lower().endswith(ext):
                without_extension = without_extension[: -len(ext)]
                break

        parts = without_extension.split("/")
        if parts and parts[-1] in ("index", "__init__"):
            parts = parts[:-1]

        return ".".join(parts) if parts else "<module>"
