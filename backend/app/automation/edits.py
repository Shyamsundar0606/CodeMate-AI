"""Exact anchored edits for larger files. No fuzzy matching or code execution."""

from pydantic import Field

from app.automation.policy import digest, reject, safe_path
from app.automation.schemas import Change, GeneratedSuggestion


class TargetedChange(Change):
    original: str = Field(min_length=1, max_length=2400)
    replacement: str = Field(min_length=1, max_length=2400)


class TargetedSuggestion(GeneratedSuggestion):
    changes: list[TargetedChange] = Field(min_length=1, max_length=4)


def expand_edits(files, suggestion):
    changes, seen = [], set()
    for edit in suggestion.changes:
        path = safe_path(edit.path)
        if path not in files or path in seen:
            raise reject("Only distinct, explicitly inspected existing files may change.")
        seen.add(path)
        before = files[path]
        if digest(before) != edit.before_sha256:
            raise reject("Patch base content hash does not match the pinned source.")
        if not edit.original.strip() or before.count(edit.original) != 1:
            raise reject(
                "The proposed edit must match exactly one nonempty source excerpt. "
                "No suggestion was saved."
            )
        after = before.replace(edit.original, edit.replacement, 1)
        changes.append(Change(path=path, before_sha256=edit.before_sha256, replacement=after))
    return GeneratedSuggestion.model_validate(
        {
            **suggestion.model_dump(exclude={"changes"}),
            "changes": changes,
        }
    )
