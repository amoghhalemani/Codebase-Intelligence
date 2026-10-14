from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.models import ParsedFile, Reference, ResolutionStatus


class SymbolResolver:
    """Resolves imports and call/attribute references into symbol IDs."""

    def __init__(self, parsed_files: list[ParsedFile], repo_root: Path):
        self.repo_root = repo_root
        self.parsed_files = {item.module_id: item for item in parsed_files}
        self.symbols_by_id: dict[str, object] = {}
        self.symbols_by_name: dict[str, list[object]] = defaultdict(list)
        self.module_aliases: dict[str, dict[str, str]] = defaultdict(dict)
        self.class_hierarchy: dict[str, list[str]] = {}

        for parsed in parsed_files:
            self.class_hierarchy.update(parsed.class_hierarchy)
            for symbol in parsed.symbols:
                self.symbols_by_id[symbol.id] = symbol
                self.symbols_by_name[symbol.qualified_name].append(symbol)
                self.symbols_by_name[symbol.name].append(symbol)

            for imported in parsed.imports:
                local_name = imported.alias or imported.local_name
                self.module_aliases[parsed.module_id][local_name] = imported.imported_path

    def resolve_all(self) -> list[ParsedFile]:
        for parsed in self.parsed_files.values():
            for reference in parsed.references:
                resolved_id = self._resolve_reference(parsed, reference)

                if resolved_id:
                    reference.target_symbol_id = resolved_id
                    reference.resolution_status = ResolutionStatus.RESOLVED
                else:
                    reference.resolution_status = ResolutionStatus.UNRESOLVED

        return list(self.parsed_files.values())

    def _resolve_reference(
        self,
        parsed: ParsedFile,
        reference: Reference,
    ) -> Optional[str]:
        if reference.reference_type == "import":
            return self._resolve_import(parsed, reference.target_name)

        target_name = reference.target_name

        if target_name.startswith(("self.", "cls.")):
            resolved = self._resolve_bound_method(parsed, reference, target_name)
            if resolved:
                return resolved

        if target_name in self.symbols_by_id:
            return target_name

        local_candidates = self.symbols_by_name.get(target_name, [])

        if len(local_candidates) == 1:
            return local_candidates[0].id

        alias_target = self.module_aliases[parsed.module_id].get(
            target_name.split(".")[0]
        )

        if alias_target:
            remainder = target_name.split(".", 1)[1] if "." in target_name else ""
            candidate = f"{alias_target}.{remainder}" if remainder else alias_target
            resolved = self._resolve_import(parsed, candidate)

            if resolved:
                return resolved

        qualified_candidates = self.symbols_by_name.get(target_name, [])

        if len(qualified_candidates) == 1:
            return qualified_candidates[0].id

        same_module = [
            symbol
            for symbol in self.symbols_by_name.get(target_name, [])
            if symbol.module == parsed.module_id
        ]

        if len(same_module) == 1:
            return same_module[0].id

        return None

    def _resolve_bound_method(
        self,
        parsed: ParsedFile,
        reference: Reference,
        target_name: str,
    ) -> Optional[str]:
        owner_prefix = target_name.split(".", 1)[0]
        member_name = target_name.split(".", 1)[1]

        if not member_name:
            return None

        class_path = self._current_class_for_symbol(reference.source_symbol_id)
        if not class_path:
            return None

        candidate_classes = {class_path}
        direct_class_key = f"{parsed.module_id}:{class_path}"
        for parent in self.class_hierarchy.get(direct_class_key, []):
            candidate_classes.add(parent)
            candidate_classes.add(f"{parsed.module_id}:{parent}")

        for class_name in candidate_classes:
            for candidate in [
                f"{parsed.module_id}:{class_name}.{member_name}",
                f"{class_name}.{member_name}",
                f"{parsed.module_id}:{class_name}.{owner_prefix}.{member_name}",
            ]:
                if candidate in self.symbols_by_id:
                    return candidate

        member_candidates = self.symbols_by_name.get(member_name, [])
        for symbol in member_candidates:
            if symbol.qualified_name.startswith(f"{class_path}."):
                return symbol.id

        for class_name in candidate_classes:
            for symbol in self.symbols_by_name.get(member_name, []):
                if symbol.qualified_name.startswith(f"{class_name}."):
                    return symbol.id

        return None

    @staticmethod
    def _current_class_for_symbol(symbol_id: Optional[str]) -> Optional[str]:
        if not symbol_id or ":" not in symbol_id:
            return None

        qualified_name = symbol_id.split(":", 1)[1]
        if "." not in qualified_name:
            return None

        return qualified_name.rsplit(".", 1)[0]

    def _resolve_import(self, parsed: ParsedFile, imported_path: str) -> Optional[str]:
        candidates = []
        lookup_values = {imported_path, f"{parsed.module_id}.{imported_path}"}

        for candidate in lookup_values:
            if candidate in self.symbols_by_id:
                candidates.append(candidate)

            dotted_name = candidate.replace(".", ":", 1) if "." in candidate and candidate.count(".") >= 1 else candidate
            if dotted_name in self.symbols_by_id:
                candidates.append(dotted_name)

        if len(candidates) == 1:
            return candidates[0]

        if "." in imported_path:
            final_name = imported_path.split(".")[-1]
            direct_matches = [
                symbol.id
                for symbol in self.symbols_by_name.get(final_name, [])
                if symbol.qualified_name.endswith(f".{final_name}")
                or symbol.id.endswith(f":{final_name}")
            ]
            if len(direct_matches) == 1:
                return direct_matches[0]

        module_symbol_ids = [
            symbol.id
            for symbol in self.symbols_by_name.get(imported_path, [])
            if symbol.module == imported_path
        ]

        if module_symbol_ids:
            return module_symbol_ids[0]

        matching_modules = [
            module_id
            for module_id in self.parsed_files
            if module_id == imported_path
            or module_id.startswith(f"{imported_path}.")
        ]

        if len(matching_modules) == 1:
            return f"{matching_modules[0]}:<module>"

        return None
