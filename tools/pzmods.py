#!/usr/bin/env python3
"""Helper CLI for developing Project Zomboid (Build 42) mods in this repo.

Commands:
  new       Create a new mod from the Build 42 template.
  validate  Check mods for structural mistakes the game fails on silently.
  link      Link mods into your Zomboid/Workshop folder so the game sees them.
  unlink    Remove those links.
  paths     Show where the game folders are expected to be.

Only the Python standard library is used, so it runs anywhere Python 3.9+ does.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODS_DIR = REPO_ROOT / "pz"
TEMPLATE_DIR = REPO_ROOT / "templates" / "b42-mod"

MOD_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,63}$")
VERSION_DIR_RE = re.compile(r"^\d+(\.\d+){0,2}$")
TOKENS = ("__MOD_ID__", "__MOD_NAME__", "__AUTHOR__", "__DESCRIPTION__")

PREVIEW_SIZE = (256, 256)
POSTER_SIZE = (512, 512)
ICON_SIZE = (64, 64)


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

def zomboid_home(override: str | None) -> Path:
    """The user's Zomboid cache folder (not the game install folder)."""
    if override:
        return Path(override).expanduser()
    env = os.environ.get("ZOMBOID_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / "Zomboid"


def list_mod_packages() -> list[Path]:
    if not MODS_DIR.is_dir():
        return []
    return sorted(p for p in MODS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def resolve_packages(names: list[str]) -> list[Path]:
    packages = list_mod_packages()
    if not names:
        return packages
    by_name = {p.name: p for p in packages}
    missing = [n for n in names if n not in by_name]
    if missing:
        raise SystemExit(f"Unknown mod folder(s) in pz/: {', '.join(missing)}")
    return [by_name[n] for n in names]


# --------------------------------------------------------------------------- #
# Placeholder images
# --------------------------------------------------------------------------- #

def write_png(path: Path, size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    """Write an 8-bit RGB PNG with a vertical gradient. Placeholder art only."""
    width, height = size
    rows = bytearray()
    for y in range(height):
        t = y / max(height - 1, 1)
        pixel = bytes(round(a + (b - a) * t) for a, b in zip(top, bottom))
        rows += b"\x00" + pixel * width

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b"")
    )


def png_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


# --------------------------------------------------------------------------- #
# new
# --------------------------------------------------------------------------- #

def cmd_new(args: argparse.Namespace) -> int:
    mod_id = args.mod_id
    if not MOD_ID_RE.match(mod_id):
        print(
            "Mod ID must start with a letter and use only letters, digits and underscores "
            "(3-64 characters), e.g. BetterRainBarrels.",
            file=sys.stderr,
        )
        return 2

    existing_ids = {info.mod_id.lower() for pkg in list_mod_packages() for info in find_mod_infos(pkg)}
    if mod_id.lower() in existing_ids:
        print(f"A mod with id '{mod_id}' already exists in pz/.", file=sys.stderr)
        return 2

    dest = MODS_DIR / mod_id
    if dest.exists():
        print(f"{dest.relative_to(REPO_ROOT)} already exists.", file=sys.stderr)
        return 2

    values = {
        "__MOD_ID__": mod_id,
        "__MOD_NAME__": args.name or re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", mod_id).replace("_", " "),
        "__AUTHOR__": args.author or "Your Name",
        "__DESCRIPTION__": args.description or "Describe what this mod does in one sentence.",
    }

    for src in sorted(TEMPLATE_DIR.rglob("*")):
        rel_path = src.relative_to(TEMPLATE_DIR).as_posix().replace("__MOD_ID__", mod_id)
        target = dest / rel_path
        if src.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        for token, value in values.items():
            value = json.dumps(value)[1:-1] if src.suffix == ".json" else value
            text = text.replace(token, value)
        target.write_text(text, encoding="utf-8", newline="\n")

    version_dir = dest / "Contents" / "mods" / mod_id / "42"
    write_png(dest / "preview.png", PREVIEW_SIZE, (52, 62, 48), (122, 30, 24))
    write_png(version_dir / "poster.png", POSTER_SIZE, (52, 62, 48), (122, 30, 24))
    write_png(version_dir / "icon.png", ICON_SIZE, (200, 170, 90), (122, 30, 24))

    print(f"Created pz/{mod_id}")
    print("Next steps:")
    print(f"  1. Edit pz/{mod_id}/Contents/mods/{mod_id}/42/mod.info and workshop.txt")
    print(f"  2. Write your Lua in pz/{mod_id}/Contents/mods/{mod_id}/42/media/lua/")
    print(f"  3. python tools/pzmods.py validate {mod_id}")
    print(f"  4. python tools/pzmods.py link {mod_id}   (then enable it in the game's Mods menu)")
    return 0


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #

@dataclass
class ModInfo:
    package: Path
    mod_dir: Path
    info_path: Path
    fields: dict[str, str]

    @property
    def mod_id(self) -> str:
        return self.fields.get("id", "")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: Path, msg: str) -> None:
        self.errors.append(f"{rel(where)}: {msg}")

    def warn(self, where: Path, msg: str) -> None:
        self.warnings.append(f"{rel(where)}: {msg}")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_key_values(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def find_mod_infos(package: Path) -> list[ModInfo]:
    infos = []
    mods_root = package / "Contents" / "mods"
    if not mods_root.is_dir():
        return infos
    for mod_dir in sorted(p for p in mods_root.iterdir() if p.is_dir()):
        candidates = [d for d in mod_dir.iterdir() if d.is_dir() and VERSION_DIR_RE.match(d.name)]
        candidates.append(mod_dir / "common")
        for folder in candidates:
            info_path = folder / "mod.info"
            if info_path.is_file():
                infos.append(ModInfo(package, mod_dir, info_path, parse_key_values(info_path)))
    return infos


def validate_package(package: Path, report: Report) -> list[ModInfo]:
    workshop = package / "workshop.txt"
    if not workshop.is_file():
        report.error(package, "missing workshop.txt (needed to upload to the Steam Workshop)")
    else:
        ws = parse_key_values(workshop)
        if not ws.get("title"):
            report.error(workshop, "missing title=")
        if ws.get("visibility") and ws["visibility"] not in {"public", "unlisted", "friendsOnly", "private"}:
            report.error(workshop, f"visibility must be public, unlisted, friendsOnly or private, not '{ws['visibility']}'")

    preview = package / "preview.png"
    if not preview.is_file():
        report.error(package, "missing preview.png (256x256 PNG, required for Workshop upload)")
    else:
        size = png_size(preview)
        if size is None:
            report.error(preview, "is not a valid PNG file")
        elif size != PREVIEW_SIZE:
            report.error(preview, f"is {size[0]}x{size[1]}, the Workshop uploader expects 256x256")
        if preview.stat().st_size > 1_000_000:
            report.error(preview, "is larger than 1000 KB")

    mods_root = package / "Contents" / "mods"
    if not mods_root.is_dir():
        report.error(package, "missing Contents/mods/ folder")
        return []

    mod_dirs = [p for p in mods_root.iterdir() if p.is_dir()]
    if not mod_dirs:
        report.error(mods_root, "contains no mod folders")

    infos = find_mod_infos(package)
    for mod_dir in mod_dirs:
        if not (mod_dir / "common").is_dir():
            report.error(mod_dir, "missing common/ folder (Build 42 expects it, even if empty)")
        if not any(i.mod_dir == mod_dir for i in infos):
            report.error(mod_dir, "no mod.info found in a version folder like 42/ (or in common/)")
        stray = mod_dir / "mod.info"
        if stray.exists():
            report.error(stray, "Build 42 ignores a mod.info at the mod root; move it into 42/")
        if (mod_dir / "media").exists():
            report.error(mod_dir / "media", "Build 42 ignores media/ at the mod root; move it into 42/ or common/")

    for info in infos:
        check_mod_info(info, report)
        check_translations(info.info_path.parent, report)
        check_leftover_tokens(info.info_path.parent, report)
    return infos


def check_mod_info(info: ModInfo, report: Report) -> None:
    f, path = info.fields, info.info_path
    if path.name != "mod.info":
        report.error(path, "file must be named exactly mod.info (lowercase)")
    for key in ("id", "name"):
        if not f.get(key):
            report.error(path, f"missing {key}=")
    mod_id = f.get("id", "")
    if mod_id and not MOD_ID_RE.match(mod_id):
        report.error(path, f"id '{mod_id}' should only contain letters, digits and underscores")
    if mod_id and mod_id != info.mod_dir.name:
        report.warn(path, f"id '{mod_id}' differs from its folder name '{info.mod_dir.name}'")
    if not f.get("versionmin"):
        report.warn(path, "no versionMin= set; add versionMin=42.0.0 so older builds skip it")
    for key in ("require", "incompatible", "loadmodafter", "loadmodbefore"):
        if "\\" in f.get(key, ""):
            report.warn(path, f"{key}= uses the deprecated backslash format; list plain mod IDs separated by commas")
    for key in ("poster", "icon"):
        name = f.get(key)
        if name and not (path.parent / name).is_file():
            report.error(path, f"{key}={name} but that file does not exist next to mod.info")


def check_translations(version_dir: Path, report: Report) -> None:
    translate = version_dir / "media" / "lua" / "shared" / "Translate"
    if not translate.is_dir():
        return
    for path in sorted(translate.rglob("*")):
        if path.suffix == ".txt":
            report.error(path, "Build 42 only loads .json translation files; .txt is ignored")
        elif path.suffix == ".json":
            try:
                json.loads(path.read_bytes().decode("utf-8"))
            except UnicodeDecodeError:
                report.error(path, "translation files must be UTF-8")
            except json.JSONDecodeError as exc:
                report.error(path, f"invalid JSON: {exc}")


def check_leftover_tokens(version_dir: Path, report: Report) -> None:
    for path in version_dir.rglob("*"):
        if path.is_file() and path.suffix in {".lua", ".info", ".json", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in TOKENS:
                if token in text:
                    report.error(path, f"still contains template placeholder {token}")


def cmd_validate(args: argparse.Namespace) -> int:
    packages = resolve_packages(args.mods)
    if not packages:
        print("No mods found in pz/. Create one with: python tools/pzmods.py new MyModId")
        return 1

    report = Report()
    seen: dict[str, Path] = {}
    for package in packages:
        for info in validate_package(package, report):
            key = info.mod_id.lower()
            if key and key in seen and seen[key] != info.mod_dir:
                report.error(info.info_path, f"id '{info.mod_id}' is also used by {rel(seen[key])}")
            seen.setdefault(key, info.mod_dir)

    for w in report.warnings:
        print(f"warning: {w}")
    for e in report.errors:
        print(f"error:   {e}")
    names = ", ".join(p.name for p in packages)
    if report.errors:
        print(f"\n{len(report.errors)} error(s) in: {names}")
        return 1
    print(f"OK: {names}" + (f" ({len(report.warnings)} warning(s))" if report.warnings else ""))
    return 0


# --------------------------------------------------------------------------- #
# link / unlink
# --------------------------------------------------------------------------- #

def is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(os.path, "isjunction", None)
    return bool(is_junction and is_junction(path))


def points_to(link: Path, target: Path) -> bool:
    try:
        return link.resolve() == target.resolve()
    except OSError:
        return False


def make_link(link: Path, target: Path) -> None:
    if os.name == "nt":
        # Junctions work without admin rights or Developer Mode, unlike symlinks.
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=True)


def remove_link(link: Path) -> None:
    if os.name == "nt" and not link.is_symlink():
        os.rmdir(link)
    else:
        link.unlink()


def cmd_link(args: argparse.Namespace) -> int:
    workshop_dir = zomboid_home(args.zomboid_dir) / "Workshop"
    if not workshop_dir.parent.is_dir():
        print(
            f"Could not find your Zomboid folder at {workshop_dir.parent}.\n"
            "Launch Project Zomboid once so it creates it, or pass --zomboid-dir / set ZOMBOID_HOME.",
            file=sys.stderr,
        )
        return 1
    workshop_dir.mkdir(exist_ok=True)

    status = 0
    for package in resolve_packages(args.mods):
        link = workshop_dir / package.name
        if is_link(link):
            if points_to(link, package):
                print(f"already linked  {link}")
                continue
            remove_link(link)
        elif link.exists():
            print(f"skipped         {link} exists and is a real folder; move it away first", file=sys.stderr)
            status = 1
            continue
        make_link(link, package)
        print(f"linked          {link} -> {rel(package)}")
    if status == 0:
        print("\nStart the game, open Mods from the main menu, and enable your mod.")
    return status


def cmd_unlink(args: argparse.Namespace) -> int:
    workshop_dir = zomboid_home(args.zomboid_dir) / "Workshop"
    for package in resolve_packages(args.mods):
        link = workshop_dir / package.name
        if is_link(link) and points_to(link, package):
            remove_link(link)
            print(f"unlinked        {link}")
        else:
            print(f"not linked      {link}")
    return 0


def cmd_paths(args: argparse.Namespace) -> int:
    home = zomboid_home(args.zomboid_dir)
    print(f"Zomboid folder:  {home}  ({'found' if home.is_dir() else 'not found'})")
    print(f"Workshop folder: {home / 'Workshop'}  (link target for development)")
    print(f"Game log:        {home / 'console.txt'}  (print() output and Lua errors)")
    print(f"Repo mods:       {MODS_DIR}")
    return 0


# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pzmods", description="Project Zomboid Build 42 mod helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create a new mod from the template")
    p.add_argument("mod_id", help="unique mod ID, e.g. BetterRainBarrels")
    p.add_argument("--name", help="display name shown in the Mods menu")
    p.add_argument("--author")
    p.add_argument("--description")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("validate", help="check mods for common mistakes")
    p.add_argument("mods", nargs="*", help="mod folders in pz/ (default: all)")
    p.set_defaults(func=cmd_validate)

    for name, func, text in (
        ("link", cmd_link, "link mods into Zomboid/Workshop"),
        ("unlink", cmd_unlink, "remove links from Zomboid/Workshop"),
        ("paths", cmd_paths, "show game folder locations"),
    ):
        p = sub.add_parser(name, help=text)
        if name != "paths":
            p.add_argument("mods", nargs="*", help="mod folders in pz/ (default: all)")
        p.add_argument("--zomboid-dir", help="your Zomboid folder (default: ~/Zomboid or $ZOMBOID_HOME)")
        p.set_defaults(func=func)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
