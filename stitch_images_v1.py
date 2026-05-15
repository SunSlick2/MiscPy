import sys
import os
import argparse
import numpy as np
from PIL import Image

# ── tuneable parameters ──────────────────────────────────────────────────────
MATCH_THRESHOLD   = 5.0   
MIN_OVERLAP_ROWS  = 2     
MAX_OVERLAP_FRAC  = 0.9   
# ─────────────────────────────────────────────────────────────────────────────

def find_overlap(top: np.ndarray, bot: np.ndarray,
                 threshold: float = MATCH_THRESHOLD,
                 min_rows: int = MIN_OVERLAP_ROWS,
                 max_frac: float = MAX_OVERLAP_FRAC) -> int:
    h_top = top.shape[0]
    h_bot = bot.shape[0]
    max_overlap = int(min(h_top, h_bot) * max_frac)

    for h in range(max_overlap, min_rows - 1, -1):
        tail = top[-h:].astype(np.float32)
        head = bot[:h].astype(np.float32)
        diff = np.mean(np.abs(tail - head))
        if diff < threshold:
            return h
    return 0

def stitch(top_path: str, bot_path: str, out_path: str,
           threshold: float = MATCH_THRESHOLD,
           verbose: bool = True) -> int:
    top_img = Image.open(top_path).convert("RGB")
    bot_img = Image.open(bot_path).convert("RGB")

    top = np.array(top_img)
    bot = np.array(bot_img)

    if top.shape[1] != bot.shape[1]:
        print(f"  Warning: Width mismatch in {top_path}. Skipping.")
        return -1

    overlap = find_overlap(top, bot, threshold=threshold)

    bot_cropped = bot[overlap:]
    stitched = np.vstack([top, bot_cropped])
    result = Image.fromarray(stitched.astype(np.uint8))
    result.save(out_path)

    if verbose:
        print(f"  Processed: {os.path.basename(out_path)} (Overlap: {overlap}px)")

    return overlap

def find_pairs(directory: str):
    """Finds pairs ending in T.png and B.png."""
    if not os.path.exists(directory):
        return []
    
    files = [f for f in os.listdir(directory) if f.lower().endswith(".png")]
    # Extract stem by removing the last character (T or B) and the extension
    tops = {f[:-5]: f for f in files if f[-5].upper() == 'T'}
    bots = {f[:-5]: f for f in files if f[-5].upper() == 'B'}
    
    pairs = []
    for stem in sorted(set(tops) & set(bots)):
        pairs.append((
            os.path.join(directory, tops[stem]),
            os.path.join(directory, bots[stem]),
            stem,
        ))
    return pairs

def main():
    # Default paths as requested
    default_in = r"C:\Users\abc\Downloads\Test\Raw"
    default_out = r"C:\Users\abc\Downloads\Test"

    parser = argparse.ArgumentParser(description="Stitch T/B image pairs.")
    parser.add_argument("--input", default=default_in, help=f"Default: {default_in}")
    parser.add_argument("--outdir", default=default_out, help=f"Default: {default_out}")
    parser.add_argument("--threshold", type=float, default=MATCH_THRESHOLD)

    args = parser.parse_args()

    pairs = find_pairs(args.input)
    if not pairs:
        print(f"No matching T/B pairs found in {args.input}")
        return

    os.makedirs(args.outdir, exist_ok=True)
    
    for top_path, bot_path, stem in pairs:
        out_path = os.path.join(args.outdir, f"{stem}_stitched.png")
        stitch(top_path, bot_path, out_path, threshold=args.threshold)

if __name__ == "__main__":
    main()
