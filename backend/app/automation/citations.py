"""Deterministic references to the exact pinned source, never model-authored quotes."""

import json
import re

from app.ai.errors import AIError
from app.automation.schemas import Citation, CitationReference


def invalid(message):
    return AIError(
        "AUTOMATION_CITATION_INVALID",
        message + " No suggestion was saved. Regenerate a concise request or inspect fewer files.",
        422,
    )


def catalog_for(files, evidence):
    catalog = {}
    for kind, sources in (("source", files), ("ci", evidence)):
        for source, content in sorted(sources.items()):
            lines = content.splitlines(keepends=True)
            group, first = [], 1

            def append(parts, start, end, *, kind=kind, source=source):
                quote = "".join(parts).rstrip("\r\n")
                if not quote.strip():
                    return
                if len(catalog) >= 192:
                    raise invalid("Source context exceeds the 192-excerpt citation budget.")
                identity = f"E{len(catalog) + 1:04d}"
                catalog[identity] = {
                    "evidence_id": identity,
                    "kind": kind,
                    "source": source,
                    "line_start": start,
                    "line_end": end,
                    "quote": quote,
                }

            for number, line in enumerate(lines, 1):
                if group and (len(group) >= 6 or sum(map(len, group)) + len(line) > 280):
                    append(group, first, number - 1)
                    group = []
                if len(line) > 280:
                    for offset in range(0, len(line), 280):
                        append([line[offset : offset + 280]], number, number)
                else:
                    if not group:
                        first = number
                    group.append(line)
            if group:
                append(group, first, len(lines))
    if not catalog:
        raise invalid("The snapshot contains no nonempty citable evidence.")
    return catalog


def resolve(references: list[CitationReference], catalog):
    citations, seen = [], set()
    for index, reference in enumerate(references, 1):
        entry = catalog.get(reference.evidence_id)
        if entry is None:
            raise invalid(f"Citation {index} uses an evidence ID absent from this snapshot.")
        if reference.evidence_id in seen:
            raise invalid(
                f"Citation {index} duplicates a reference instead of supplying distinct evidence."
            )
        seen.add(reference.evidence_id)
        if reference.line_start is not None or reference.line_end is not None:
            if (reference.line_start, reference.line_end) != (
                entry["line_start"],
                entry["line_end"],
            ):
                raise invalid(f"Citation {index} has a line range not supplied by the backend.")
        citations.append(
            Citation(
                source=entry["source"],
                quote=entry["quote"],
                evidence_id=entry["evidence_id"],
                line_start=entry["line_start"],
                line_end=entry["line_end"],
            )
        )
    return citations


def wire_schema(model, catalog):
    schema = model.model_json_schema()
    reference = schema["$defs"]["CitationReference"]
    # The model selects an ID only. Path, range and quote are backend-owned data.
    reference["properties"] = {"evidence_id": {"type": "string", "enum": list(catalog)}}
    reference["required"] = ["evidence_id"]
    reference["additionalProperties"] = False
    return schema


def parse_output(model, content):
    if not isinstance(content, str):
        raise ValueError("Expected structured JSON")
    fenced = re.fullmatch(r"\s*```(?:json)?\s*\n([\s\S]*?)\n```\s*", content)
    if fenced:
        content = fenced.group(1)
    # Fences/JSON whitespace are formatting only. No repair or remapping of data.
    value = json.loads(content)
    return model.model_validate(value)
