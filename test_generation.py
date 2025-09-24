#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

import server
import numpy as np
import cv2 as cv

def create_test_face(color, size=300):
    """Create a simple colored square image for testing"""
    colors = {
        'WHITE': (255, 255, 255),
        'RED': (0, 0, 255),
        'GREEN': (0, 255, 0),
        'YELLOW': (0, 255, 255),
        'ORANGE': (0, 165, 255),
        'BLUE': (255, 0, 0)
    }
    
    img = np.full((size, size, 3), colors.get(color, (128, 128, 128)), dtype=np.uint8)
    return img

def test_cube_string_generation():
    """Test the complete cube string generation process"""
    print("=== Testing Cube String Generation ===")
    
    # Create test face images (solved cube)
    face_imgs = {
        'U': create_test_face('WHITE'),
        'R': create_test_face('RED'), 
        'F': create_test_face('GREEN'),
        'D': create_test_face('YELLOW'),
        'L': create_test_face('ORANGE'),
        'B': create_test_face('BLUE')
    }
    
    try:
        # Call the internal functions directly
        centroids, face_to_cube_mapping = server._calibrate_centroids(face_imgs)
        print("Centroids calibrated successfully")
        print("Face to cube mapping:", face_to_cube_mapping)
        
        cube_string = server._build_cube_string(face_imgs, centroids, face_to_cube_mapping)
        print(f"Generated cube string: {cube_string}")
        print(f"Length: {len(cube_string)}")
        
        # Test validation with kociemba
        import kociemba
        try:
            solution = kociemba.solve(cube_string)
            print(f"✓ Valid cube string! Solution: {solution}")
            return True
        except Exception as e:
            print(f"✗ Invalid cube string: {e}")
            return False
            
    except Exception as e:
        print(f"Error in cube string generation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_cube_string_generation()