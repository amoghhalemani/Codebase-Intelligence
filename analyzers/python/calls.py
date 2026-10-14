import ast
from typing import Optional

from core.models import Reference


class CallVisitor(ast.NodeVisitor):
    def __init__(
        self,
        module_id: str,
        file_path: str,
        scopes: dict[int, str],
    ):
        self.module_id = module_id
        self.file_path = file_path
        self.scopes = scopes
        self.references: list[Reference] = []
        self.current_symbol = f"{module_id}:<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_callable(node)

    def _visit_callable(self, node: ast.AST) -> None:
        previous = self.current_symbol
        self.current_symbol = self.scopes.get(
            node.lineno,
            f"{self.module_id}:<module>",
        )
        self.generic_visit(node)
        self.current_symbol = previous

    def visit_Call(self, node: ast.Call) -> None:
        target_name = self._call_name(node.func)

        if target_name:
            self.references.append(
                Reference(
                    source_symbol_id=self.current_symbol,
                    target_name=target_name,
                    target_symbol_id=None,
                    reference_type="call",
                    resolution_status="unresolved",
                    file=self.file_path,
                    line=node.lineno,
                )
            )

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        target_name = self._dotted_name(node)

        if target_name:
            self.references.append(
                Reference(
                    source_symbol_id=self.current_symbol,
                    target_name=target_name,
                    target_symbol_id=None,
                    reference_type="attribute",
                    resolution_status="unresolved",
                    file=self.file_path,
                    line=node.lineno,
                )
            )

        self.generic_visit(node)

    @staticmethod
    def _call_name(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            return CallVisitor._dotted_name(node)

        return None

    @staticmethod
    def _dotted_name(node: ast.AST) -> Optional[str]:
        parts: list[str] = []

        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value

        if isinstance(node, ast.Name):
            parts.append(node.id)
            return ".".join(reversed(parts))

        return None
