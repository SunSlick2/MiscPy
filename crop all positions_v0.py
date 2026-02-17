import os
from pathlib import Path
# Assuming your previous logic is in border_remover.py
from border_remover import crop_png_bottom

def process_windows_folder(target_dir):
    # Convert string to a Windows-friendly Path object
    base_path = Path(target_dir)
    
    if not base_path.exists():
        print(f"Error: The path {base_path} could not be found.")
        return

    # Create an output folder in the same directory
    output_folder = base_path / "Processed_Output"
    output_folder.mkdir(exist_ok=True)

    count = 0
    # iterate through the directory
    for file_path in base_path.glob("*.png"):
        # Check if filename (without .png) ends with 'Position'
        if file_path.stem.endswith("Position"):
            
            # Construct new filename: OriginalName + 0 + .png
            new_name = f"{file_path.stem}0{file_path.suffix}"
            save_path = output_folder / new_name
            
            print(f"Windows Processing: {file_path.name} -> {new_name}")
            
            # Run the cropping function
            # We convert the Path objects back to strings for OpenCV compatibility
            crop_png_bottom(str(file_path), str(save_path))
            count += 1

    print(f"\nFinished! {count} Windows files updated in: {output_folder}")

# --- WINDOWS PATH CONFIGURATION ---
# Use an 'r' before the quotes to create a "Raw String"
# This prevents Windows backslashes from causing errors.
windows_path = r"C:\Users\YourName\Documents\MyImages" 

process_windows_folder(windows_path)