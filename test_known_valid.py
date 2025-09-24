#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

import server
import numpy as np
import cv2 as cv
import kociemba

def create_mixed_face_from_string(pattern, size=300):
    """Create a face with a specific color pattern from a string"""
    colors = {
        'U': (255, 255, 255),  # WHITE
        'R': (0, 0, 255),      # RED
        'F': (0, 255, 0),      # GREEN
        'D': (0, 255, 255),    # YELLOW
        'L': (0, 165, 255),    # ORANGE
        'B': (255, 0, 0)       # BLUE
    }
    
    img = np.zeros((size, size, 3), dtype=np.uint8)
    tile_size = size // 3
    
    for i, color_char in enumerate(pattern):
        row = i // 3
        col = i % 3
        y1, y2 = row * tile_size, (row + 1) * tile_size
        x1, x2 = col * tile_size, (col + 1) * tile_size
        
        color = colors.get(color_char, (128, 128, 128))
        img[y1:y2, x1:x2] = color
    
    return img

def test_known_valid_scrambled():
    """Test with a known valid scrambled cube state"""
    print("=== Testing Known Valid Scrambled Cube ===")
    
    # Use the known valid scrambled cube string
    valid_scrambled = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL"
    
    # Parse into faces
    faces = {
        'U': valid_scrambled[0:9],
        'R': valid_scrambled[9:18],
        'F': valid_scrambled[18:27],
        'D': valid_scrambled[27:36],
        'L': valid_scrambled[36:45],
        'B': valid_scrambled[45:54]
    }
    
    print("Known valid cube faces:")
    for face, pattern in faces.items():
        print(f"  {face}: {pattern}")
    
    # Create images from this pattern
    face_imgs = {}
    for face, pattern in faces.items():
        face_imgs[face] = create_mixed_face_from_string(pattern)
    
    try:
        # Process through our pipeline
        centroids, face_to_cube_mapping = server._calibrate_centroids(face_imgs)
        print("Face to cube mapping:", face_to_cube_mapping)
        
        cube_string = server._build_cube_string(face_imgs, centroids, face_to_cube_mapping)
        print(f"Generated cube string: {cube_string}")
        print(f"Original cube string:  {valid_scrambled}")
        print(f"Strings match: {cube_string == valid_scrambled}")
        
        # Test both
        print("\n=== Testing Original ===")
        try:
            solution = kociemba.solve(valid_scrambled)
            print(f"✓ Original valid: {len(solution.split())} moves")
        except Exception as e:
            print(f"✗ Original invalid: {e}")
            
        print("\n=== Testing Generated ===")
        try:
            solution = kociemba.solve(cube_string)
            print(f"✓ Generated valid: {len(solution.split())} moves")
            return True
        except Exception as e:
            print(f"✗ Generated invalid: {e}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_known_valid_scrambled()