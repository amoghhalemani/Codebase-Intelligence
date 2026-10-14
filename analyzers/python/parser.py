import ast
from pathlib import Path

from analyzers.base import BaseAnalyzer
from analyzers.python.calls import CallVisitor
from analyzers.python.imports import ImportVisitor
from analyzers.python.symbols import SymbolVisitor
from core.models import ParsedFile


class PythonAnalyzer(BaseAnalyzer):
    language = "python"

    def supports_file(self, path: Path) -> bool:
        return path.suffix == ".py"

    def parse_file(self, path: Path, repo_root: Path) -> ParsedFile:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))

        relative_path = path.relative_to(repo_root).as_posix()
        module_id = self._module_id(relative_path)

        symbol_visitor = SymbolVisitor(module_id, relative_path)
        symbol_visitor.visit(tree)

        import_visitor = ImportVisitor(module_id, relative_path)
        import_visitor.visit(tree)

        call_visitor = CallVisitor(module_id, relative_path, symbol_visitor.scopes)
        call_visitor.visit(tree)

        class_hierarchy = {}
        for class_node in ast.walk(tree):
            if not isinstance(class_node, ast.ClassDef):
                continue
            bases = []
            for base in class_node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            class_hierarchy[f"{module_id}:{class_node.name}"] = bases

        return ParsedFile(
            path=relative_path,
            module_id=module_id,
            language=self.language,
            symbols=symbol_visitor.symbols,
            imports=import_visitor.imports,
            references=call_visitor.references,
            class_hierarchy=class_hierarchy,
        )

    @staticmethod
    def _module_id(relative_path: str) -> str:
        without_extension = relative_path.removesuffix(".py")
        parts = without_extension.split("/")

        if parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join(parts) if parts else "<module>"
