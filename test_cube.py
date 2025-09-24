#!/usr/bin/env python3

import kociemba
from collections import Counter

def test_cube_string(cube_string):
    print(f"Testing cube string: {cube_string}")
    print(f"Length: {len(cube_string)}")
    
    # Count each face
    counts = Counter(cube_string)
    print(f"Face counts: {dict(counts)}")
    
    # Check if each face has exactly 9 stickers
    valid_counts = all(count == 9 for count in counts.values())
    print(f"Valid counts (9 each): {valid_counts}")
    
    # Test with kociemba
    try:
        solution = kociemba.solve(cube_string)
        print(f"✓ Solution found: {len(solution.split())} moves")
        print(f"Solution: {solution}")
        return True
    except Exception as e:
        print(f"✗ Kociemba error: {e}")
        return False

if __name__ == "__main__":
    # Test our current cube string
    current_string = "FBFRUBRDBRFRURFLUFDLDLFLDDUBBLRDULRRUBDFLUBFFBDURBDLLU"
    print("=== Testing Current Cube String ===")
    test_cube_string(current_string)
    
    print("\n=== Testing Known Valid Cube String ===")
    # Test a known valid solved cube
    solved_string = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
    test_cube_string(solved_string)
    
    print("\n=== Testing Known Invalid Cube String ===")
    # Test an invalid cube string (too many of one color)
    invalid_string = "UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU"
    test_cube_string(invalid_string)