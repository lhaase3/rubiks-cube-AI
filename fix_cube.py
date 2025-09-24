#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

import server
import kociemba
from collections import Counter

def validate_cube_edges(cube_string):
    """Check if all edges match between adjacent faces"""
    if len(cube_string) != 54:
        return False, "Invalid length"
        
    faces = {
        'U': cube_string[0:9],
        'R': cube_string[9:18], 
        'F': cube_string[18:27],
        'D': cube_string[27:36],
        'L': cube_string[36:45],
        'B': cube_string[45:54]
    }
    
    # Define edge relationships (face1, pos1, face2, pos2)
    # Position mapping: 0 1 2
    #                   3 4 5  (4 is center)
    #                   6 7 8
    edges = [
        ('U', 1, 'B', 1),  # U top - B top
        ('U', 3, 'L', 1),  # U left - L top  
        ('U', 5, 'R', 1),  # U right - R top
        ('U', 7, 'F', 1),  # U bottom - F top
        ('R', 3, 'F', 5),  # R left - F right
        ('R', 5, 'B', 3),  # R right - B left
        ('R', 7, 'D', 5),  # R bottom - D right
        ('F', 3, 'L', 5),  # F left - L right
        ('F', 7, 'D', 1),  # F bottom - D top
        ('D', 3, 'L', 7),  # D left - L bottom
        ('D', 7, 'B', 7),  # D bottom - B bottom
        ('B', 5, 'L', 3),  # B right - L left
    ]
    
    errors = []
    for face1, pos1, face2, pos2 in edges:
        color1 = faces[face1][pos1]
        color2 = faces[face2][pos2]
        if color1 != color2:
            errors.append(f"{face1}[{pos1}]={color1} != {face2}[{pos2}]={color2}")
    
    if errors:
        return False, f"Edge mismatches: {'; '.join(errors[:5])}"  # Show first 5
    
    return True, "All edges match"

def fix_cube_string_simple(cube_string):
    """Try to fix a cube string by making it solvable"""
    # Strategy: Keep the center colors but create a valid solved state
    faces = {
        'U': cube_string[0:9],
        'R': cube_string[9:18], 
        'F': cube_string[18:27],
        'D': cube_string[27:36],
        'L': cube_string[36:45],
        'B': cube_string[45:54]
    }
    
    # Extract centers (position 4 of each face)
    centers = {face: face_data[4] for face, face_data in faces.items()}
    print("Centers:", centers)
    
    # Create a solved cube with these centers
    fixed_faces = {}
    for face, center in centers.items():
        fixed_faces[face] = [center] * 9
    
    fixed_string = "".join("".join(fixed_faces[face]) for face in ['U', 'R', 'F', 'D', 'L', 'B'])
    return fixed_string

def test_cube_fixing():
    """Test the cube fixing approach"""
    problematic = "FBFRUBRDBRFRURFLUFDLDLFLDDUBBLRDULRRUBDFLUBFFBDURBDLLU"
    
    print("=== Original Cube Analysis ===")
    valid, msg = validate_cube_edges(problematic)
    print(f"Valid: {valid}")
    print(f"Message: {msg}")
    
    print("\n=== Attempting to Fix ===")
    fixed = fix_cube_string_simple(problematic)
    print(f"Fixed cube: {fixed}")
    
    valid, msg = validate_cube_edges(fixed)
    print(f"Fixed valid: {valid}")
    print(f"Fixed message: {msg}")
    
    print("\n=== Testing with Kociemba ===")
    try:
        solution = kociemba.solve(fixed)
        print(f"✓ Fixed solution: {solution}")
    except Exception as e:
        print(f"✗ Fixed still invalid: {e}")

if __name__ == "__main__":
    test_cube_fixing()