#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

import server
import numpy as np
import cv2 as cv
import kociemba

def create_realistic_face(center_color, scrambled_colors, size=300):
    """Create a face image with the correct center but scrambled edge/corner colors"""
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
    
    # Use center_color for position 4, scrambled_colors for others
    pattern = scrambled_colors[:4] + [center_color] + scrambled_colors[4:8]
    
    for i, color_char in enumerate(pattern):
        row = i // 3
        col = i % 3
        y1, y2 = row * tile_size, (row + 1) * tile_size
        x1, x2 = col * tile_size, (col + 1) * tile_size
        
        color = colors.get(color_char, (128, 128, 128))
        img[y1:y2, x1:x2] = color
    
    return img

def test_realistic_scrambled_cube():
    """Test with realistic scrambled cube colors"""
    print("=== Testing Realistic Scrambled Cube ===")
    
    # Define scrambled patterns but keep centers correct
    face_patterns = {
        'U': ['R', 'F', 'D', 'L', 'U', 'B', 'F', 'R', 'D'],  # U center = WHITE
        'R': ['U', 'B', 'L', 'F', 'R', 'D', 'B', 'U', 'L'],  # R center = RED
        'F': ['D', 'R', 'U', 'B', 'F', 'L', 'R', 'D', 'U'],  # F center = GREEN
        'D': ['F', 'L', 'B', 'R', 'D', 'U', 'L', 'F', 'B'],  # D center = YELLOW
        'L': ['B', 'U', 'R', 'D', 'L', 'F', 'U', 'B', 'R'],  # L center = ORANGE
        'B': ['L', 'D', 'F', 'U', 'B', 'R', 'D', 'L', 'F']   # B center = BLUE
    }
    
    # Create images from these patterns
    face_imgs = {}
    for face, pattern in face_patterns.items():
        center = pattern[4]  # Should match the face
        scrambled = pattern[:4] + pattern[5:]  # All except center
        face_imgs[face] = create_realistic_face(center, scrambled)
    
    print("Face patterns:")
    for face, pattern in face_patterns.items():
        print(f"  {face}: {''.join(pattern)} (center: {pattern[4]})")
    
    try:
        # Process through our pipeline
        centroids, face_to_cube_mapping = server._calibrate_centroids(face_imgs)
        print("Face to cube mapping:", face_to_cube_mapping)
        
        cube_string = server._build_cube_string(face_imgs, centroids, face_to_cube_mapping)
        print(f"Generated cube string: {cube_string}")
        print(f"Length: {len(cube_string)}")
        
        # Test validation
        try:
            solution = kociemba.solve(cube_string)
            print(f"✓ Valid cube string! Solution length: {len(solution.split())} moves")
            return True
        except Exception as e:
            print(f"✗ Invalid cube string: {e}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_realistic_scrambled_cube()