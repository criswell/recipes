#!/usr/bin/env python3
"""Generate recipe indexes from directory structure.

Walks category subdirectories, extracts recipe titles from markdown files,
and generates:
  - A per-category README.md in each category directory
  - An auto-generated index section in the root README.md
"""

import re
from pathlib import Path

INDEX_START = "<!-- INDEX:START -->"
INDEX_END = "<!-- INDEX:END -->"

Recipe = tuple  # (path: Path, title: str)


def extract_title(path: Path) -> str:
    """Extract the first H1 heading from a markdown file, or derive from filename."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^#\s+(.+)$", line)
            if m:
                return m.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def discover_categories(root: Path) -> dict[str, list[Recipe]]:
    """Find all category directories and their recipe files."""
    categories = {}
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        recipes = []
        for md in sorted(d.glob("*.md")):
            if md.name.lower() == "readme.md":
                continue
            title = extract_title(md)
            recipes.append((md, title))
        if recipes:
            categories[d.name] = recipes
    return categories


def category_display_name(name: str) -> str:
    """Convert directory name to display title."""
    return name.replace("-", " ").replace("_", " ").title()


def write_category_readme(category_dir: Path, recipes: list[Recipe]) -> None:
    """Generate a README.md inside a category directory."""
    name = category_display_name(category_dir.name)
    lines = [f"# {name}\n"]
    for path, title in sorted(recipes, key=lambda r: r[1].lower()):
        lines.append(f"- [{title}]({path.name})")
    lines.append("")
    category_dir.joinpath("README.md").write_text("\n".join(lines), encoding="utf-8")


def build_index_section(root: Path, categories: dict[str, list[Recipe]]) -> str:
    """Build the markdown index section for the root README."""
    if not categories:
        return ""
    lines = [INDEX_START, "", "## Recipes", ""]
    for cat_name, recipes in sorted(categories.items()):
        lines.append(f"### {category_display_name(cat_name)}")
        lines.append("")
        for path, title in sorted(recipes, key=lambda r: r[1].lower()):
            rel = path.relative_to(root)
            lines.append(f"- [{title}]({rel})")
        lines.append("")
    lines.append(INDEX_END)
    return "\n".join(lines)


def update_root_readme(root: Path, categories: dict[str, list[Recipe]]) -> None:
    """Update the root README.md with the generated index section."""
    readme = root / "README.md"
    if not readme.exists():
        return

    content = readme.read_text(encoding="utf-8")
    index_section = build_index_section(root, categories)

    start = content.find(INDEX_START)
    end = content.find(INDEX_END)

    if start != -1 and end != -1:
        # Replace existing index
        if index_section:
            content = content[:start] + index_section + content[end + len(INDEX_END):]
        else:
            # No recipes — remove the index section entirely
            # Also strip a leading newline if present
            before = content[:start].rstrip("\n")
            after = content[end + len(INDEX_END):]
            content = before + after
    elif index_section:
        # Append new index
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + index_section + "\n"

    readme.write_text(content, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parent
    categories = discover_categories(root)

    for cat_name, recipes in categories.items():
        write_category_readme(root / cat_name, recipes)

    update_root_readme(root, categories)


if __name__ == "__main__":
    main()
