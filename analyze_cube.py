#!/usr/bin/env python3

import kociemba
from collections import Counter

def analyze_cube_string(cube_string):
    """Analyze what makes a cube string invalid"""
    print(f"Analyzing cube string: {cube_string}")
    print(f"Length: {len(cube_string)}")
    
    # Count each face
    counts = Counter(cube_string)
    print(f"Face counts: {dict(counts)}")
    
    # Parse into faces
    faces = {
        'U': cube_string[0:9],
        'R': cube_string[9:18], 
        'F': cube_string[18:27],
        'D': cube_string[27:36],
        'L': cube_string[36:45],
        'B': cube_string[45:54]
    }
    
    print("\nFace breakdown:")
    for face, pattern in faces.items():
        print(f"  {face}: {pattern}")
        print(f"     Center: {pattern[4]}")
    
    # Check edge and corner constraints
    print("\nEdge analysis:")
    # U-R edge should have same colors
    u_right = faces['U'][5]  # Right edge of U face
    r_top = faces['R'][1]    # Top edge of R face
    print(f"  U-R edge: U[5]={u_right}, R[1]={r_top}, match: {u_right == r_top}")
    
    # U-F edge
    u_bottom = faces['U'][7]  # Bottom edge of U face
    f_top = faces['F'][1]     # Top edge of F face
    print(f"  U-F edge: U[7]={u_bottom}, F[1]={f_top}, match: {u_bottom == f_top}")
    
    # More edges...
    print("\nTrying to solve with kociemba:")
    try:
        solution = kociemba.solve(cube_string)
        print(f"✓ Valid! Solution: {solution}")
    except Exception as e:
        print(f"✗ Invalid: {e}")

def create_valid_alternative():
    """Try to create a valid cube string with the same color distribution"""
    # Use the same color counts but in a different arrangement
    original = "FBFRUBRDBRFRURFLUFDLDLFLDDUBBLRDULRRUBDFLUBFFBDURBDLLU"
    
    # Try a simple rearrangement that maintains face centers
    # Keep centers the same but shuffle the edges/corners
    
    faces = {
        'U': list("UUUUUUUUU"),  # All white
        'R': list("RRRRRRRRR"),  # All red 
        'F': list("FFFFFFFFF"),  # All green
        'D': list("DDDDDDDDD"),  # All yellow
        'L': list("LLLLLLLLL"),  # All orange
        'B': list("BBBBBBBBB")   # All blue
    }
    
    # Now scramble a bit but keep it valid
    valid_string = "".join("".join(face) for face in faces.values())
    print(f"\nTesting solved cube: {valid_string}")
    
    try:
        solution = kociemba.solve(valid_string)
        print(f"✓ Solved cube valid: {solution}")
    except Exception as e:
        print(f"✗ Even solved cube invalid: {e}")

if __name__ == "__main__":
    # Analyze the problematic cube string
    problematic = "FBFRUBRDBRFRURFLUFDLDLFLDDUBBLRDULRRUBDFLUBFFBDURBDLLU"
    analyze_cube_string(problematic)
    
    create_valid_alternative()