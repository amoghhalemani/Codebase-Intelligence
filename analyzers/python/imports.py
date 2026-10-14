import ast

from core.models import Import, Reference


class ImportVisitor(ast.NodeVisitor):
    def __init__(self, module_id: str, file_path: str):
        self.module_id = module_id
        self.file_path = file_path
        self.imports: list[Import] = []
        self.references: list[Reference] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            imported_name = alias.asname or alias.name.split(".")[0]
            self._record(node, alias.name, imported_name, alias.asname is not None)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        level = node.level or 0

        for alias in node.names:
            imported_name = alias.asname or alias.name
            full_name = f"{module}.{alias.name}" if module else alias.name
            self._record(node, full_name, imported_name, alias.asname is not None, level)

        self.generic_visit(node)

    def _record(
        self,
        node: ast.AST,
        imported_path: str,
        local_name: str,
        aliased: bool,
        level: int = 0,
    ) -> None:
        self.imports.append(
            Import(
                module=self.module_id,
                file=self.file_path,
                imported_path=imported_path,
                local_name=local_name,
                alias=local_name if aliased else None,
                level=level,
                line=node.lineno,
            )
        )

        self.references.append(
            Reference(
                source_symbol_id=f"{self.module_id}:<module>",
                target_name=imported_path,
                target_symbol_id=None,
                reference_type="import",
                resolution_status="unresolved",
                file=self.file_path,
                line=node.lineno,
            )
        )
