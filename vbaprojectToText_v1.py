from pathlib import Path
from oletools.olevba import VBA_Parser

# Set working directory to your specific folder
target_dir = Path(r"C:\users\abc")
bin_path = target_dir / "vbaProject.bin"
output_path = target_dir / "extracted_code.txt"

if not bin_path.exists():
    print(f"Error: Could not find {bin_path}")
else:
    vb_parser = VBA_Parser(str(bin_path))

    if vb_parser.detect_vba_macros():
        with open(output_path, "w", encoding="utf-8") as f:
            for filename, stream_path, vba_filename, vba_code in vb_parser.extract_macros():
                f.write(f"' === Module: {vba_filename} ===\n\n")
                f.write(vba_code)
                f.write("\n\n" + "=" * 40 + "\n\n")
        print(f"Success! Extracted VBA code saved to: {output_path}")
    else:
        print("No VBA macros found in the target file.")

    vb_parser.close()
