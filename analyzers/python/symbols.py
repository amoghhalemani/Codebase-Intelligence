import ast
import hashlib
from typing import Optional

from core.models import Symbol


class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, module_id: str, file_path: str):
        self.module_id = module_id
        self.file_path = file_path
        self.symbols: list[Symbol] = []
        self.scopes: dict[int, str] = {}
        self.scope_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add_symbol(node, node.name, "class")
        self.scopes[node.lineno] = f"{self.module_id}:{self._qualified_name(node.name)}"
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._add_symbol(node, node.name, "function")
        self.scopes[node.lineno] = f"{self.module_id}:{self._qualified_name(node.name)}"
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._add_symbol(node, node.name, "async_function")
        self.scopes[node.lineno] = f"{self.module_id}:{self._qualified_name(node.name)}"
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._add_symbol(node, target.id, "variable")

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            self._add_symbol(node, node.target.id, "variable")

        self.generic_visit(node)

    def _add_symbol(
        self,
        node: ast.AST,
        name: str,
        kind: str,
    ) -> None:
        qualified_name = self._qualified_name(name)
        end_line = getattr(node, "end_lineno", node.lineno)

        self.symbols.append(
            Symbol(
                id=f"{self.module_id}:{qualified_name}",
                name=name,
                qualified_name=qualified_name,
                kind=kind,
                file=self.file_path,
                module=self.module_id,
                start_line=node.lineno,
                end_line=end_line,
                signature=self._signature(node),
            )
        )

    def _qualified_name(self, name: str) -> str:
        return ".".join([*self.scope_stack, name])

    @staticmethod
    def _signature(node: ast.AST) -> Optional[str]:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        try:
            args = ast.unparse(node.args)
        except Exception:
            args = ""

        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({args})"


def stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
