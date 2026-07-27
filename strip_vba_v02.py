"""
strip_vba.py

For a single .xlsm file:
  1. Extracts all VBA module source code to text files (via oletools) so you
     can review/edit them (e.g. remove Shell() calls) before rebuilding.
  2. Strips the VBA project from the workbook so it opens cleanly in desktop
     Excel (useful when ASR/EDR policies block macro-enabled files).

Requires: pip install oletools --user
(oletools is pure-Python, no admin rights needed for --user install)

Usage:
    1. Edit SRC_FILE below to point at your .xlsm
    2. python strip_vba.py

Output (written into the SAME folder as SRC_FILE):
    <name>_vba_modules/ModuleName.bas / .cls / .frm  (one per VBA module)
    <name>_clean.xlsx                                (macro-free copy)
    Original file is left untouched.
"""

# ============================================================
# CONFIG — edit this path before running
# ============================================================
SRC_FILE = r"C:\path\to\your\file.xlsm"
# ============================================================

import sys
import re
import shutil
import zipfile
from pathlib import Path

try:
    from oletools.olevba import VBA_Parser
except ImportError:
    VBA_Parser = None


VBA_RELATIONSHIP_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/vbaProject"
VBA_PART_NAME = "/xl/vbaProject.bin"
MACRO_CONTENT_TYPE = "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
STANDARD_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"


def strip_relationship(xml_text: str) -> str:
    """Remove the <Relationship .../> element pointing at vbaProject.bin."""
    pattern = re.compile(
        r'<Relationship[^>]*Type="' + re.escape(VBA_RELATIONSHIP_TYPE) + r'"[^>]*/>'
    )
    new_text, n = pattern.subn("", xml_text)
    if n == 0:
        print("    [!] No vbaProject relationship found in workbook.xml.rels (already clean?)")
    else:
        print(f"    Removed {n} vbaProject relationship entr{'y' if n==1 else 'ies'}")
    return new_text


def strip_content_type_override(xml_text: str) -> str:
    """Remove the <Override .../> entry for /xl/vbaProject.bin."""
    pattern = re.compile(
        r'<Override[^>]*PartName="' + re.escape(VBA_PART_NAME) + r'"[^>]*/>'
    )
    new_text, n = pattern.subn("", xml_text)
    if n == 0:
        print("    [!] No vbaProject Override found in [Content_Types].xml (already clean?)")
    else:
        print("    Removed vbaProject Override entry")
    return new_text


def fix_workbook_content_type(xml_text: str) -> str:
    """Switch workbook.xml content type from macro-enabled to standard."""
    if MACRO_CONTENT_TYPE not in xml_text:
        print("    [!] Macro-enabled content type not found (already standard?)")
        return xml_text
    new_text = xml_text.replace(MACRO_CONTENT_TYPE, STANDARD_CONTENT_TYPE)
    print("    Switched workbook.xml content type to standard (non-macro)")
    return new_text


MODULE_EXT = {
    1: ".bas",   # standard module
    2: ".cls",   # class module
    3: ".frm",   # form
    100: ".cls", # document module (ThisWorkbook, sheets) - saved as .cls
}


def extract_vba_modules(src_path: Path) -> Path:
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
        # vba_filename is usually like "ModuleName.bas" already; normalize
        stem = Path(vba_filename).stem
        ext = Path(vba_filename).suffix or ".bas"
        out_path = out_dir / f"{stem}{ext}"
        out_path.write_text(vba_code, encoding="utf-8")
        print(f"    Extracted: {out_path.name}")
        count += 1

    parser.close()
    print(f"    -> {count} module(s) written to {out_dir.name}/")

    # Flag Shell( calls for convenience
    print("    Scanning for Shell() references...")
    for f in out_dir.glob("*.*"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r'\bShell\s*\(', line, re.IGNORECASE):
                print(f"      {f.name}:{i}: {line.strip()}")

    return out_dir


def scan_for_leftover_macro_refs(contents: dict) -> list:
    """
    After stripping vbaProject.bin, scan every XML part for anything still
    referencing macros — e.g. button/shape macro="..." attributes,
    ActiveX ctrlProps, or leftover vba strings. Returns list of (name, match)
    tuples found.
    """
    findings = []
    patterns = [
        re.compile(r'macro="[^"]*"', re.IGNORECASE),
        re.compile(r'vbProcedure', re.IGNORECASE),
        re.compile(r'xl/vbaProject', re.IGNORECASE),
    ]
    for name, data in contents.items():
        if not name.endswith(".xml") and not name.endswith(".rels"):
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for pat in patterns:
            for m in pat.finditer(text):
                findings.append((name, m.group(0)))
    return findings


def strip_macro_attributes(contents: dict) -> dict:
    """Remove macro="..." attributes from drawing/shape XML parts."""
    macro_attr_pattern = re.compile(r'\s*macro="[^"]*"', re.IGNORECASE)
    for name in list(contents.keys()):
        if "drawing" in name.lower() and name.endswith(".xml"):
            text = contents[name].decode("utf-8")
            new_text, n = macro_attr_pattern.subn("", text)
            if n > 0:
                print(f"    Removed {n} macro attribute(s) from {name}")
                contents[name] = new_text.encode("utf-8")
    return contents


def process_file(src_path: Path) -> Path:
    print(f"\nProcessing: {src_path.name}")

    print("  [1/2] Extracting VBA source...")
    extract_vba_modules(src_path)

    print("  [2/2] Stripping VBA project from workbook...")
    dest_path = src_path.with_name(src_path.stem + "_clean.xlsx")
    if dest_path.exists():
        dest_path.unlink()

    # Work on a temp copy so we don't touch the original
    tmp_zip = src_path.with_name(src_path.stem + "_tmp.zip")
    shutil.copy(src_path, tmp_zip)

    with zipfile.ZipFile(tmp_zip, "r") as zin:
        names = zin.namelist()
        contents = {name: zin.read(name) for name in names}

    if "xl/vbaProject.bin" not in contents:
        print("    [!] No xl/vbaProject.bin found in archive — nothing to strip")
    else:
        del contents["xl/vbaProject.bin"]
        print("    Deleted xl/vbaProject.bin")

    # Edit rels
    rels_path = "xl/_rels/workbook.xml.rels"
    if rels_path in contents:
        text = contents[rels_path].decode("utf-8")
        text = strip_relationship(text)
        contents[rels_path] = text.encode("utf-8")

    # Edit [Content_Types].xml
    ct_path = "[Content_Types].xml"
    if ct_path in contents:
        text = contents[ct_path].decode("utf-8")
        text = strip_content_type_override(text)
        text = fix_workbook_content_type(text)
        contents[ct_path] = text.encode("utf-8")

    # Strip macro="..." attributes from buttons/shapes in drawings
    contents = strip_macro_attributes(contents)

    # Diagnostic: anything else still referencing macros?
    leftovers = scan_for_leftover_macro_refs(contents)
    if leftovers:
        print("    [!] Remaining macro references found (may still trigger warning):")
        for name, match in leftovers:
            print(f"        {name}: {match}")
    else:
        print("    No leftover macro references found")

    # Write new zip as .xlsx
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
