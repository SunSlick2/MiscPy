import os
from pathlib import Path
# Ensure your previous script is saved as border_remover.py
from border_remover import crop_png_bottom

def process_and_rename_images(folder_path):
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' not found.")
        return

    # Optional: Create an output folder to keep originals safe
    output_folder = os.path.join(folder_path, "processed")
    os.makedirs(output_folder, exist_ok=True)

    count = 0
    for filename in os.listdir(folder_path):
        p = Path(filename)
        
        # Filter for PNGs ending in "Position"
        if p.stem.endswith("Position") and p.suffix.lower() == ".png":
            # Construct the new filename: Name + 0 + .png
            new_filename = f"{p.stem}0{p.suffix}"
            
            input_path = os.path.join(folder_path, filename)
            output_path = os.path.join(output_folder, new_filename)
            
            print(f"Cropping {filename} -> Saving as {new_filename}")
            
            # Call your function from the other script
            crop_png_bottom(input_path, output_path)
            count += 1

    print(f"\nTask Complete. {count} files processed and appended with '0'.")

# Set your directory here
process_and_rename_images("./my_images")