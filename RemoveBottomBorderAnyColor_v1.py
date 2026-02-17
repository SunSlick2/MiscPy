import cv2
import numpy as np

def crop_bottom_border_by_color(image_path, output_path, tolerance=10):
    # Load with Alpha channel
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return

    height, width = img.shape[:2]
    
    # 1. Identify the background color from the very bottom-left pixel
    # This automatically detects if the background is black, white, or transparent
    bg_color = img[height - 1, 0, :].astype(np.int16)

    crop_line = height

    # 2. Scan from bottom to top
    for r in range(height - 1, -1, -1):
        row = img[r, :, :].astype(np.int16)
        
        # Calculate how much every pixel in the row differs from the background color
        # diffs will have the same shape as the row
        diffs = np.abs(row - bg_color)
        
        # If any pixel in the row differs from the BG by more than the tolerance,
        # it means we've hit text (even if the text has 2, 3, or 50 colors).
        if np.any(np.sum(diffs, axis=1) > tolerance):
            # We found text! The border ends at the row below this one.
            crop_line = r + 1
            break
        else:
            # This row is purely background color
            crop_line = r

    # 3. Save the result
    # Ensure we don't crop the whole image if no border is found
    if crop_line < height:
        cropped_img = img[0:crop_line, :]
        cv2.imwrite(output_path, cropped_img)
        print(f"Removed {height - crop_line} pixels of background. Saved: {output_path}")
    else:
        print(f"No border detected for {image_path}")