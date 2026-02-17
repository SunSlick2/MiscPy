import cv2
import numpy as np

def crop_png_bottom(image_path, output_path, tolerance=15):
    # Load with Alpha channel
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        print(f"Error: Could not open {image_path}")
        return

    height, width = img.shape[:2]
    crop_line = height

    # Scan from bottom to top
    for r in range(height - 1, -1, -1):
        row = img[r, :, :]
        
        # Calculate how much each pixel differs from the very first pixel in the row
        # This is much more effective for 'noisy' borders
        first_pixel = row[0]
        diffs = np.abs(row.astype(np.int16) - first_pixel.astype(np.int16))
        row_diff_score = np.mean(diffs)

        # If the average difference in the row is very low, it's a border
        if row_diff_score < tolerance:
            crop_line = r
        else:
            # We hit a row with significant detail/color change
            break

    # If crop_line is still height, nothing was found to crop
    if crop_line == height:
        print("No border detected. Try increasing the tolerance.")
        return

    cropped_img = img[0:crop_line, :]
    cv2.imwrite(output_path, cropped_img)
    print(f"Success: Cropped {height - crop_line} pixels from bottom.")