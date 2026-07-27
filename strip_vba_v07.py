"""
strip_vba.py

  1. Extract all VBA module source to text files (via oletools) for review.
  2. Minimal VBA-project removal from a .xlsm file:
     - Copy the file
     - Delete xl/vbaProject.bin
     - Remove the vbaProject Override from [Content_Types].xml
     - Remove the vbaProject Relationship from xl/_rels/workbook.xml.rels
     - Rezip, output as .xls

Note: renaming to .xls does NOT convert the file to the legacy binary
format — it's still a zip/OOXML package internally, just with a .xls
extension. Excel may flag a format/extension mismatch on open.

Requires: pip install oletools --user

Usage:
    1. Edit SRC_FILE below
    2. python strip_vba.py

Output (same folder as SRC_FILE):
    <name>_vba_modules/ModuleName.bas / .cls / .frm
    <name>_clean.xls
Original file is left untouched.
"""

# ============================================================
# CONFIG — edit this path before running
# ============================================================
SRC_FILE = r"C:\path\to\your\file.xlsm"
# ============================================================

import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Optional

try:
    from oletools.olevba import VBA_Parser
except ImportError:
    VBA_Parser = None

VBA_RELATIONSHIP_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/vbaProject"
VBA_PART_NAME = "/xl/vbaProject.bin"


def safe_decode(data: bytes) -> Optional[str]:
    """Decode bytes as text, trying common encodings. Returns None if the
    data isn't decodable as text at all (i.e. it's actually binary) —
    callers must check for None rather than assuming success."""
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def extract_vba_modules(src_path: Path) -> Optional[Path]:
    """Extract each VBA module's source to its own file for review/editing."""
    if VBA_Parser is None:
        print("    [!] oletools not installed — skipping extraction.")
        print("        Install with: pip install oletools --user")
        return None

    out_dir = src_path.with_name(src_path.stem + "_vba_modules")
    out_dir.mkdir(exist_ok=True)

    parser = VBA_Parser(str(src_path))
    if not parser.detect_vba_macros():
        print("    [!] No VBA macros detected in this file")
        parser.close()
        return out_dir

    count = 0
    for (_, _, vba_filename, vba_code) in parser.extract_macros():
        if vba_code is None:
            continue
        stem = Path(vba_filename).stem
        ext = Path(vba_filename).suffix or ".bas"
        out_path = out_dir / f"{stem}{ext}"
        out_path.write_text(vba_code, encoding="utf-8")
        print(f"    Extracted: {out_path.name}")
        count += 1

    parser.close()
    print(f"    -> {count} module(s) written to {out_dir.name}/")

    print("    Scanning for Shell() references...")
    for f in out_dir.glob("*.*"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r'\bShell\s*\(', line, re.IGNORECASE):
                print(f"      {f.name}:{i}: {line.strip()}")

    return out_dir


def process_file(src_path: Path) -> Path:
    print(f"\nProcessing: {src_path.name}")

    print("  [1/2] Extracting VBA source...")
    extract_vba_modules(src_path)

    print("  [2/2] Stripping VBA project from workbook...")
    dest_path = src_path.with_name(src_path.stem + "_clean.xls")
    if dest_path.exists():
        dest_path.unlink()

    # 1. Copy the file to a temp zip
    tmp_zip = src_path.with_name(src_path.stem + "_tmp.zip")
    shutil.copy(src_path, tmp_zip)

    with zipfile.ZipFile(tmp_zip, "r") as zin:
        contents = {name: zin.read(name) for name in zin.namelist()}

    # 2. Delete xl/vbaProject.bin
    if "xl/vbaProject.bin" in contents:
        del contents["xl/vbaProject.bin"]
        print("    Deleted xl/vbaProject.bin")
    else:
        print("    [!] xl/vbaProject.bin not found — nothing to delete")

    # 3. Remove vbaProject Override from [Content_Types].xml
    ct_path = "[Content_Types].xml"
    if ct_path in contents:
        text = safe_decode(contents[ct_path])
        if text is None:
            print(f"    [!] Could not decode {ct_path} as text — skipping this edit")
        else:
            pattern = re.compile(
                r'<Override[^>]*PartName="' + re.escape(VBA_PART_NAME) + r'"[^>]*/>'
            )
            new_text, n = pattern.subn("", text)
            if n:
                print(f"    Removed vbaProject Override from {ct_path}")
            else:
                print(f"    [!] No vbaProject Override found in {ct_path}")
            contents[ct_path] = new_text.encode("utf-8")

    # 4. Remove vbaProject Relationship from xl/_rels/workbook.xml.rels
    rels_path = "xl/_rels/workbook.xml.rels"
    if rels_path in contents:
        text = safe_decode(contents[rels_path])
        if text is None:
            print(f"    [!] Could not decode {rels_path} as text — skipping this edit")
        else:
            pattern = re.compile(
                r'<Relationship[^>]*Type="' + re.escape(VBA_RELATIONSHIP_TYPE) + r'"[^>]*/>'
            )
            new_text, n = pattern.subn("", text)
            if n:
                print(f"    Removed vbaProject Relationship from {rels_path}")
            else:
                print(f"    [!] No vbaProject Relationship found in {rels_path}")
            contents[rels_path] = new_text.encode("utf-8")

    # 5. Rezip, output as .xls
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in contents.items():
            zout.writestr(name, data)

    tmp_zip.unlink()
    print(f"    -> Wrote {dest_path.name}")
    return dest_path


def main():
    src = Path(SRC_FILE)
    if not src.exists():
        print(f"[!] File not found: {src}")
        sys.exit(1)
    if src.suffix.lower() != ".xlsm":
        print(f"[!] Expected .xlsm, got: {src.suffix}")
        sys.exit(1)

    process_file(src)
    print("\nDone.")


if __name__ == "__main__":
    main()
