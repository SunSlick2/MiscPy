import cv2
import numpy as np

def crop_png_bottom(image_path, output_path, std_threshold=0.5):
    # 1. Load with IMREAD_UNCHANGED to keep the Alpha channel
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        print("Error: Could not open the image.")
        return

    # Get dimensions (height, width, and potentially channels)
    height, width = img.shape[:2]
    crop_line = height

    # 2. Scan from Bottom to Top
    # We stop as soon as we find a row with visual "texture"
    for r in range(height - 1, -1, -1):
        row = img[r, :, :]
        
        # Calculate standard deviation across all channels (R, G, B, and A)
        row_std = np.std(row)

        if row_std < std_threshold:
            # This row is a solid color/transparent; mark it for removal
            crop_line = r
        else:
            # We found actual image content
            break

    # 3. Slice the image from the top (0) to the crop_line
    cropped_img = img[0:crop_line, :]
    
    # 4. Save the result
    cv2.imwrite(output_path, cropped_img)
    print(f"Done! Removed {height - crop_line} pixels from the bottom.")

# Example usage:
crop_png_bottom("input_file.png", "cleaned_bottom.png")