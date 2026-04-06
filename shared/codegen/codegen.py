#!/usr/bin/env python3
"""
codegen.py - CppFolio prebuild code generator
Reads: data/data.json + templates/*.html
Emits: generated/data.hpp + generated/pages.hpp
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True, choices=["portfolio", "blog"])
args = parser.parse_args()

ROOT = Path(__file__).parent.parent.parent
DATA_FILE = ROOT / "shared" / "data" / args.project / "data.json"
TPL_DIR = ROOT / args.project / "templates"
OUT_DIR = ROOT / args.project / "generated"
SHARED_TPL_DIR = ROOT / "shared" / "templates"

PAGES = [
    "index",
    "about",
    "projects",
    "contact",
    "resume",
    "uses",
    "now",
    "testimonials",
    "hire",
    "changelog",
    "not_found",
    "explore",
]


# ── Segment types ──────────────────────────────────────────────────────────


@dataclass
class Literal:
    text: str


@dataclass
class Scalar:
    key: str


@dataclass
class LoopField:
    var: str
    field: str


@dataclass
class LoopLeaf:
    var: str


@dataclass
class LoopBlock:
    array: str
    var: str
    inner: list = field(default_factory=list)


# ── Step 1: load JSON ──────────────────────────────────────────────────────


def load_json() -> tuple[dict, dict]:
    if not DATA_FILE.exists():
        sys.exit(f"ERROR: {DATA_FILE} not found")
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: data.json: {e}")

    scalars = {}
    arrays = {}
    for k, v in raw.items():
        if isinstance(v, str):
            scalars[k] = v
        elif isinstance(v, list):
            arrays[k] = v
        else:
            print(
                f"[WARN] unexpected JSON type for key '{k}': {type(v)}", file=sys.stderr
            )

    return scalars, arrays


# ── Helpers ────────────────────────────────────────────────────────────────


def c_escape(s: str) -> str:
    """Escape a string for use inside fixed_str("...") in C++."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


# ── Step 2: resolve includes ───────────────────────────────────────────────


def resolve_includes(source: str, stack: list[str]) -> str:
    def replacer(m):
        partial = m.group(1).strip()
        path = TPL_DIR / partial
        if not path.exists():
            path = SHARED_TPL_DIR / partial
        if not path.exists():
            sys.exit(f"ERROR: include not found: {partial}")
        if str(path) in stack:
            sys.exit(f"ERROR: circular include: {' -> '.join(stack + [str(path)])}")
        content = path.read_text(encoding="utf-8")
        return resolve_includes(content, stack + [str(path)])

    return re.sub(r"\{\{include (.+?)\}\}", replacer, source)


# ── Step 3: extract {{meta}} ───────────────────────────────────────────────


def extract_meta(source: str) -> tuple[dict, str]:
    first_line = source.split("\n")[0].strip()
    m = re.match(r"\{\{meta (.+?)\}\}", first_line)
    if not m:
        return {}, source
    attrs = dict(re.findall(r'(\w+)="([^"]+)"', m.group(1)))
    source = source[source.index("\n") + 1 :]
    return attrs, source


# ── Step 4: parse into segments ────────────────────────────────────────────


def find_matching_each_close(source: str, start: int) -> int:
    """Find the {{/each}} that closes the block starting at `start`.
    Handles nested loops by tracking depth."""
    depth = 1
    pos = start
    while pos < len(source):
        open_pos = source.find("{{#each ", pos)
        close_pos = source.find("{{/each}}", pos)

        if close_pos == -1:
            return -1

        if open_pos != -1 and open_pos < close_pos:
            depth += 1
            pos = open_pos + 1
        else:
            depth -= 1
            if depth == 0:
                return close_pos
            pos = close_pos + 1

    return -1


def parse(source: str, loop_var: str | None = None) -> list:
    segments = []
    pos = 0

    while pos < len(source):
        start = source.find("{{", pos)
        if start == -1:
            if source[pos:]:
                segments.append(Literal(source[pos:]))
            break

        if start > pos:
            segments.append(Literal(source[pos:start]))

        end = source.index("}}", start) + 2
        token = source[start + 2 : end - 2].strip()

        if token.startswith("#each "):
            m = re.match(r"#each ([\w.]+) as (\w+)", token)
            if not m:
                sys.exit(f"ERROR: malformed #each token: {{{{{token}}}}}")
            array_name = m.group(1)
            var_name = m.group(2)

            close = find_matching_each_close(source, end)
            if close == -1:
                sys.exit(f"ERROR: unclosed #each {array_name}")

            inner_source = source[end:close]
            inner_segs = parse(inner_source, loop_var=var_name)
            segments.append(LoopBlock(array_name, var_name, inner_segs))
            pos = close + len("{{/each}}")
            continue

        elif token == "/each":
            break

        elif loop_var and token.startswith(loop_var + "."):
            f = token.split(".", 1)[1]
            segments.append(LoopField(loop_var, f))

        elif loop_var and token == loop_var:
            segments.append(LoopLeaf(loop_var))

        else:
            segments.append(Scalar(token))

        pos = end

    return segments


# ── Emit helpers ───────────────────────────────────────────────────────────


def emit_loop(
    seg: LoopBlock,
    arrays: dict,
    scalars: dict,
    lines: list,
    prefix: str = "",
    outer_item: dict | None = None,
    emitted: set | None = None,
) -> str:
    """
    Emit Layer 1 (item vars) + Layer 2 (block var) for one loop.
    Returns the block variable name so build_chain can reference it.
    Guards against double-emission via the emitted set.
    """
    if emitted is None:
        emitted = set()

    if "." in seg.array:
        field_name = seg.array.split(".", 1)[1]
        items = outer_item.get(field_name, []) if outer_item else []
        array_key = seg.array.replace(".", "_")
    else:
        items = arrays.get(seg.array.lower(), [])
        array_key = seg.array.lower()

    block_var = f"{prefix}{array_key}_block"

    # Guard: already emitted - just return the name
    if block_var in emitted:
        return block_var
    emitted.add(block_var)

    if not items:
        print(f"[WARN] array '{seg.array}' not found or empty", file=sys.stderr)
        lines.append(f'inline constexpr auto {block_var} = fixed_str("");')
        lines.append("")
        return block_var

    item_var_names = []

    for i, item in enumerate(items):
        item_var = f"{prefix}{array_key}_item_{i}"
        chain = build_chain(
            seg.inner,
            item=item,
            scalars=scalars,
            arrays=arrays,
            lines=lines,
            prefix=f"{prefix}{array_key}_{i}_",
            emitted=emitted,
        )
        lines.append(f"inline constexpr auto {item_var} =")
        lines.append(f"    {chain};")
        lines.append("")
        item_var_names.append(item_var)

    lines.append(f"inline constexpr auto {block_var} =")
    lines.append("    " + " +\n    ".join(item_var_names) + ";")
    lines.append("")

    return block_var


def build_chain(
    segments: list,
    item: dict | str | None = None,
    scalars: dict | None = None,
    arrays: dict | None = None,
    lines: list | None = None,
    prefix: str = "",
    emitted: set | None = None,
) -> str:
    """
    Walk a segment list and produce a fixed_string chain expression.
    Nested LoopBlocks are emitted immediately into lines and referenced
    by their block variable name.
    """
    if emitted is None:
        emitted = set()

    parts = []

    for seg in segments:
        if isinstance(seg, Literal):
            if seg.text.strip():
                parts.append(f'fixed_str("{c_escape(seg.text)}")')

        elif isinstance(seg, Scalar):
            value = (scalars or {}).get(seg.key, "")
            if not value:
                print(f"[WARN] unknown scalar {{{{{seg.key}}}}}", file=sys.stderr)
            parts.append(f'fixed_str("{c_escape(str(value))}")')

        elif isinstance(seg, LoopField):
            value = item.get(seg.field, "") if isinstance(item, dict) else ""
            parts.append(f'fixed_str("{c_escape(str(value))}")')

        elif isinstance(seg, LoopLeaf):
            value = item if isinstance(item, str) else ""
            parts.append(f'fixed_str("{c_escape(value)}")')

        elif isinstance(seg, LoopBlock):
            if lines is not None and arrays is not None:
                block_var = emit_loop(
                    seg,
                    arrays,
                    scalars or {},
                    lines,
                    prefix=prefix,
                    outer_item=item if isinstance(item, dict) else None,
                    emitted=emitted,
                )
                parts.append(block_var)
            else:
                parts.append(seg.array.lower().replace(".", "_") + "_block")

    if not parts:
        return 'fixed_str("")'
    return " +\n        ".join(parts)


# ── emit_data_hpp ──────────────────────────────────────────────────────────


def emit_data_hpp(scalars: dict, arrays: dict) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    lines = []

    lines += [
        "/* AUTO-GENERATED by scripts/codegen.py - DO NOT EDIT */",
        "#pragma once",
        "",
        "#include <string_view>",
        "",
        "namespace portfolio::data {",
        "",
    ]

    for key, value in scalars.items():
        escaped = c_escape(value)
        lines.append(
            f'inline constexpr std::string_view {key} = R"_CV_({escaped})_CV_";'
        )

    STRUCT_MAP = {
        "skills_core": ("Skill", ["name"]),
        "skills_tools": ("Skill", ["name"]),
        "languages": ("Language", ["name", "level"]),
        "experience": ("Experience", ["company", "role", "period", "description"]),
        "education": ("Education", ["institution", "degree", "direction", "period"]),
        "projects": ("Project", ["name", "description", "url"]),
        "uses": ("Uses", ["category"]),
        "testimonials": ("Testimonial", ["name", "role", "company", "text"]),
        "changelog": ("Changelog", ["version", "date"]),
    }

    lines.append("")

    emitted_structs = set()
    for array_key, (struct_name, fields) in STRUCT_MAP.items():
        if array_key not in arrays:
            continue
        if struct_name in emitted_structs:
            continue
        emitted_structs.add(struct_name)
        lines.append(f"struct {struct_name} {{")
        for f in fields:
            lines.append(f"    std::string_view {f};")
        lines.append("};")
        lines.append("")

    for array_key, (struct_name, fields) in STRUCT_MAP.items():
        if array_key not in arrays:
            continue
        lines.append(f"inline constexpr {struct_name} {array_key}[] = {{")
        for item in arrays[array_key]:
            values = ", ".join(
                f'R"_CV_({c_escape(str(item.get(f, "")))})_CV_"' for f in fields
            )
            lines.append(f"    {{ {values} }},")
        lines.append("};")
        lines.append("")

    NESTED_MAP = {
        "experience": "achievements",
        "projects": "tags",
        "uses": "items",
        "changelog": "changes",
    }

    for array_key, nested_key in NESTED_MAP.items():
        if array_key not in arrays:
            continue
        for i, item in enumerate(arrays[array_key]):
            nested = item.get(nested_key, [])
            values = ", ".join(f'R"_CV_({c_escape(v)})_CV_"' for v in nested)
            var_name = f"{array_key}_{nested_key}_{i}"
            lines.append(
                f"inline constexpr std::string_view {var_name}[] = {{ {values} }};"
            )
        lines.append("")

    lines += ["", "} /* namespace portfolio::data */", ""]

    out = OUT_DIR / "data.hpp"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"codegen: wrote {out}")


# ── emit_pages_hpp ─────────────────────────────────────────────────────────


def emit_pages_hpp(scalars: dict, arrays: dict) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    lines = []

    lines += [
        "/* AUTO-GENERATED by scripts/codegen.py - DO NOT EDIT */",
        "#pragma once",
        "",
        '#include "include/fixed_string.hpp"',
        '#include "generated/data.hpp"',
        "",
        "namespace portfolio::pages {",
        "",
    ]

    base_source = (TPL_DIR / "base.html").read_text(encoding="utf-8")

    for page_name in PAGES:
        page_file = TPL_DIR / f"{page_name}.html"
        if not page_file.exists():
            sys.exit(f"ERROR: {page_file} not found")

        body_source = page_file.read_text(encoding="utf-8")

        meta, body_source = extract_meta(body_source)
        nav = meta.get("nav", "").upper()
        title = meta.get("title", page_name.capitalize())

        page_scalars = dict(scalars)
        page_scalars["META_TITLE"] = title
        for p in ["HOME", "ABOUT", "PROJECTS", "CONTACT"]:
            page_scalars[f"NAV_{p}"] = "active" if p == nav else ""

        full_source = base_source.replace("{{CONTENT}}", body_source)
        full_source = resolve_includes(full_source, [str(TPL_DIR / "base.html")])

        for key, value in page_scalars.items():
            full_source = full_source.replace(f"{{{{{key}}}}}", value)

        segments = parse(full_source)

        lines.append(f"// {'=' * 60}")
        lines.append(f"// PAGE: {page_name}")
        lines.append(f"// {'=' * 60}")
        lines.append("")

        emitted: set[str] = set()

        # Layer 1 + 2: top-level loops
        for seg in segments:
            if isinstance(seg, LoopBlock):
                emit_loop(
                    seg,
                    arrays,
                    page_scalars,
                    lines,
                    prefix=f"{page_name}_",
                    emitted=emitted,
                )

        # Layer 3: page variable
        chain = build_chain(
            segments,
            scalars=page_scalars,
            arrays=arrays,
            lines=lines,
            prefix=f"{page_name}_",
            emitted=emitted,
        )
        lines.append(f"inline constexpr auto {page_name} =")
        lines.append(f"    {chain};")
        lines.append("")

    lines += ["", "} /* namespace portfolio::pages */", ""]

    out = OUT_DIR / "pages.hpp"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"codegen: wrote {out}")


# ── main ───────────────────────────────────────────────────────────────────


def main():
    scalars, arrays = load_json()
    emit_data_hpp(scalars, arrays)
    emit_pages_hpp(scalars, arrays)


if __name__ == "__main__":
    main()
