#!/usr/bin/env python3
"""Generate recipe indexes from directory structure.

Walks category subdirectories, extracts recipe titles from markdown files,
and generates:
  - A recipe links section (between markers) in each category README.md
  - An auto-generated index section in the root README.md
"""

import re
from pathlib import Path

INDEX_START = "<!-- INDEX:START -->"
INDEX_END = "<!-- INDEX:END -->"
RECIPES_START = "<!-- RECIPES:START -->"
RECIPES_END = "<!-- RECIPES:END -->"

Recipe = tuple  # (path: Path, title: str)


def extract_title(path: Path) -> str:
    """Extract the first H1 heading from a markdown file, or derive from filename."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^#\s+(.+)$", line)
            if m:
                return m.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def extract_first_sentence(path: Path) -> str:
    """Extract the first sentence of body text after the H1 heading."""
    found_heading = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not found_heading:
                if re.match(r"^#\s+", line):
                    found_heading = True
                continue
            stripped = line.strip()
            if not stripped:
                continue
            # Skip markdown markers, headings, etc.
            if stripped.startswith(("#", "<!--", "- ", "* ", ">")):
                continue
            # Found body text — extract first sentence
            m = re.match(r"([^.!?]+[.!?])", stripped)
            if m:
                return m.group(1).strip()
            return stripped
    return ""


def read_category_info(category_dir: Path) -> tuple[str, str]:
    """Read the display name and first sentence from a category's README.md.

    Returns (display_name, first_sentence). Falls back to directory name
    if no README.md exists.
    """
    readme = category_dir / "README.md"
    if readme.exists():
        title = extract_title(readme)
        sentence = extract_first_sentence(readme)
        return title, sentence
    fallback = category_dir.name.replace("-", " ").replace("_", " ").title()
    return fallback, ""


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


def update_category_readme(category_dir: Path, recipes: list[Recipe]) -> None:
    """Update the recipe links section in a category's README.md."""
    readme = category_dir / "README.md"
    if not readme.exists():
        return

    content = readme.read_text(encoding="utf-8")
    links = [RECIPES_START, ""]
    for path, title in sorted(recipes, key=lambda r: r[1].lower()):
        links.append(f"- [{title}]({path.name})")
    links.extend(["", RECIPES_END])
    recipe_section = "\n".join(links)

    start = content.find(RECIPES_START)
    end = content.find(RECIPES_END)

    if start != -1 and end != -1:
        content = content[:start] + recipe_section + content[end + len(RECIPES_END):]
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + recipe_section + "\n"

    readme.write_text(content, encoding="utf-8")


def build_index_section(root: Path, categories: dict[str, list[Recipe]]) -> str:
    """Build the markdown index section for the root README."""
    if not categories:
        return ""
    lines = [INDEX_START, "", "## Recipes", ""]
    for cat_name, recipes in sorted(categories.items()):
        cat_dir = root / cat_name
        display_name, first_sentence = read_category_info(cat_dir)
        lines.append(f"### [{display_name}]({cat_name}/README.md)")
        if first_sentence:
            lines.extend(["", first_sentence])
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
        if index_section:
            content = content[:start] + index_section + content[end + len(INDEX_END):]
        else:
            before = content[:start].rstrip("\n")
            after = content[end + len(INDEX_END):]
            content = before + after
    elif index_section:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + index_section + "\n"

    readme.write_text(content, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parent
    categories = discover_categories(root)

    for cat_name, recipes in categories.items():
        update_category_readme(root / cat_name, recipes)

    update_root_readme(root, categories)


if __name__ == "__main__":
    main()
