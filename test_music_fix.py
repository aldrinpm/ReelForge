#!/usr/bin/env python3
"""
Quick test to verify the background music fix is working.
This script checks the BED_OFFSET_DB value and fade durations in assemble_video.py.
"""

import re
import sys

def check_assemble_video():
    """Check that the music mix parameters are set correctly."""
    
    with open('E:/AI-Video-Production/scripts/assemble_video.py', 'r') as f:
        content = f.read()
    
    # Check BED_OFFSET_DB
    bed_offset_match = re.search(r'BED_OFFSET_DB = (\d+\.\d+)', content)
    if bed_offset_match:
        bed_offset = float(bed_offset_match.group(1))
        if bed_offset == 6.0:
            print("[PASS] BED_OFFSET_DB = 6.0 (CORRECT - music will be audible)")
        else:
            print(f"[FAIL] BED_OFFSET_DB = {bed_offset} (SHOULD BE 6.0)")
            return False
    else:
        print("[FAIL] Could not find BED_OFFSET_DB")
        return False
    
    # Check fade_in
    fade_in_match = re.search(r'fade_in = min\((0\.\d+|\d+\.?\d*), timeline \* (0\.\d+)\)', content)
    if fade_in_match:
        fade_in_max = float(fade_in_match.group(1))
        fade_in_factor = float(fade_in_match.group(2))
        if fade_in_max == 0.5 and fade_in_factor == 0.08:
            print(f"[PASS] fade_in = min({fade_in_max}, timeline * {fade_in_factor}) (CORRECT)")
        else:
            print(f"[FAIL] fade_in = min({fade_in_max}, timeline * {fade_in_factor}) (SHOULD BE min(0.5, timeline * 0.08))")
            return False
    else:
        print("[FAIL] Could not find fade_in")
        return False
    
    # Check fade_out
    fade_out_match = re.search(r'fade_out = min\((0\.\d+|\d+\.?\d*), timeline \* (0\.\d+)\)', content)
    if fade_out_match:
        fade_out_max = float(fade_out_match.group(1))
        fade_out_factor = float(fade_out_match.group(2))
        if fade_out_max == 1.0 and fade_out_factor == 0.10:
            print(f"[PASS] fade_out = min({fade_out_max}, timeline * {fade_out_factor}) (CORRECT)")
        else:
            print(f"[FAIL] fade_out = min({fade_out_max}, timeline * {fade_out_factor}) (SHOULD BE min(1.0, timeline * 0.10))")
            return False
    else:
        print("[FAIL] Could not find fade_out")
        return False
    
    return True

if __name__ == '__main__':
    print("Testing background music fix...")
    print("-" * 50)
    
    if check_assemble_video():
        print("-" * 50)
        print("All checks passed! Background music should now be audible.")
        sys.exit(0)
    else:
        print("-" * 50)
        print("Some checks failed. Please review the changes.")
        sys.exit(1)
