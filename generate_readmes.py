#!/usr/bin/env python3
"""Generate image index READMEs for the raid folders in this repository."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from urllib.parse import quote


IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
DEFAULT_REPOSITORY = "SavageLemmings/RaidplanImages"
DEFAULT_BRANCH = "main"
PREVIEW_WIDTH = 240


def image_files(folder: Path) -> list[Path]:
    """Return the directly contained images in predictable, friendly order."""
    if not folder.is_dir():
        return []
    return sorted(
        (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.name.casefold(),
    )


def markdown_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")


def raw_url(repository: str, branch: str, relative_path: Path) -> str:
    encoded_path = quote(relative_path.as_posix(), safe="/")
    encoded_branch = quote(branch, safe="/")
    return f"https://raw.githubusercontent.com/{repository}/{encoded_branch}/{encoded_path}"


def table(title: str, label: str, images: list[Path], root: Path, repository: str, branch: str) -> list[str]:
    lines = [f"## {title}", "", f"| {label} | Preview | Direct link |", "|---|---|---|"]
    for image in images:
        url = raw_url(repository, branch, image.relative_to(root))
        name = markdown_text(image.name)
        alt = html.escape(image.name, quote=True)
        lines.append(
            f'| {name} | <img src="{url}" alt="{alt}" width="{PREVIEW_WIDTH}"> '
            f"| [Raw image]({url})<br>{url} |"
        )
    return lines


def render_readme(section: Path, root: Path, repository: str, branch: str) -> str:
    normal_images = image_files(section)
    map_images = image_files(section / "maps")
    lines = [
        f"# {section.name}",
        "",
        "Click **Raw image** to copy a direct GitHub URL for Discord or other external use.",
        "",
    ]
    lines.extend(table("Normal images", "Image", normal_images, root, repository, branch))
    if map_images:
        lines.extend([""])
        lines.extend(table("Maps", "Map", map_images, root, repository, branch))
    return "\n".join(lines) + "\n"


def discover_sections(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and (image_files(path) or image_files(path / "maps"))
        ),
        key=lambda path: path.name.casefold(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate README.MD image indexes. With no section names, all raid folders are updated.",
    )
    parser.add_argument("sections", nargs="*", help="Folder name(s) to update, e.g. ForkedTowerOfMagic")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY, help="GitHub owner/repository")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Branch used in raw image URLs")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    if args.sections:
        sections = [root / name for name in args.sections]
        missing = [path.name for path in sections if not path.is_dir()]
        if missing:
            parser.error(f"section folder(s) not found: {', '.join(missing)}")
    else:
        sections = discover_sections(root)

    for section in sections:
        output = section / "README.MD"
        output.write_text(render_readme(section, root, args.repository, args.branch), encoding="utf-8", newline="\n")
        print(f"Generated {output.relative_to(root)}")


if __name__ == "__main__":
    main()
