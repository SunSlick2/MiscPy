import cv2
import numpy as np

def crop_bottom_with_margin(image_path, output_path, tolerance=10):
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return

    height, width = img.shape[:2]
    
    # 1. Identify background color from bottom-left corner
    bg_color = img[height - 1, 0, :].astype(np.int16)

    # Default to no crop if no text is found
    final_crop_line = height 

    # 2. Scan from bottom to top to find the first 'text' pixel
    for r in range(height - 1, -1, -1):
        row = img[r, :, :].astype(np.int16)
        
        # Calculate difference from background
        diffs = np.abs(row - bg_color)
        row_diff_score = np.sum(diffs, axis=1)
        
        if np.any(row_diff_score > tolerance):
            # We found the last row of text at index 'r'.
            # To include this row AND one row of BG below it:
            # We need to cut at r + 2 (since slice is exclusive)
            final_crop_line = min(r + 2, height) 
            break

    # 3. Apply the crop
    if final_crop_line < height:
        cropped_img = img[0:final_crop_line, :]
        cv2.imwrite(output_path, cropped_img)
        print(f"Cropped. Kept text + 1px margin. New height: {final_crop_line}")
    else:
        print(f"No border significant enough to crop in {image_path}")