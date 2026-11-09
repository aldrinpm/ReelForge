import struct
from pathlib import Path

def verify_png(path):
    with open(path, 'rb') as f:
        # Check PNG signature
        signature = f.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            return False, "Invalid PNG signature"
        
        # IHDR chunk
        # Length (4 bytes), Chunk Type (4 bytes), Width (4 bytes), Height (4 bytes)
        # We skip the first 8 bytes (signature)
        # The first chunk is always IHDR.
        length = struct.unpack('>I', f.read(4))[0]
        chunk_type = f.read(4)
        if chunk_type != b'IHDR':
            return False, "Missing IHDR chunk"
        
        width = struct.unpack('>I', f.read(4))[0]
        height = struct.unpack('>I', f.read(4))[0]
        
    return True, (width, height)

def main():
    images_dir = Path(r"E:\AI-Video-Production\images")
    targets = [
        "scene_03_v2.png",
        "scene_04_v2.png",
        "scene_05_v2.png",
        "scene_06_v2.png",
    ]
    
    all_passed = True
    for target in targets:
        path = images_dir / target
        if not path.exists():
            print(f"{target}: FILE NOT FOUND")
            all_passed = False
            continue
            
        success, result = verify_png(path)
        if success:
            print(f"{target}: PASSED (Dimensions: {result[0]}x{result[1]})")
        else:
            print(f"{target}: FAILED ({result})")
            all_passed = False
            
    if all_passed:
        print("\nAll regenerated images verified successfully.")
    else:
        print("\nSome images failed verification.")

if __name__ == '__main__':
    main()
