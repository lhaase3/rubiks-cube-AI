#!/usr/bin/env python3

import kociemba

def analyze_valid_cube():
    """Analyze the edge relationships in a valid solved cube"""
    solved = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
    
    faces = {
        'U': solved[0:9],
        'R': solved[9:18], 
        'F': solved[18:27],
        'D': solved[27:36],
        'L': solved[36:45],
        'B': solved[45:54]
    }
    
    print("Solved cube faces:")
    for face, pattern in faces.items():
        print(f"  {face}: {pattern}")
        print(f"     Positions: 0={pattern[0]} 1={pattern[1]} 2={pattern[2]}")
        print(f"                3={pattern[3]} 4={pattern[4]} 5={pattern[5]}")
        print(f"                6={pattern[6]} 7={pattern[7]} 8={pattern[8]}")
        print()
    
    # Test a scrambled but valid cube
    scrambled = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL"
    
    print("Scrambled cube faces:")
    faces_scrambled = {
        'U': scrambled[0:9],
        'R': scrambled[9:18], 
        'F': scrambled[18:27],
        'D': scrambled[27:36],
        'L': scrambled[36:45],
        'B': scrambled[45:54]
    }
    
    for face, pattern in faces_scrambled.items():
        print(f"  {face}: {pattern}")
        print(f"     Positions: 0={pattern[0]} 1={pattern[1]} 2={pattern[2]}")
        print(f"                3={pattern[3]} 4={pattern[4]} 5={pattern[5]}")
        print(f"                6={pattern[6]} 7={pattern[7]} 8={pattern[8]}")
        print()
    
    # Now let's check what edges should match
    print("Expected edge relationships (from cube geometry):")
    print("U face edges should match:")
    print(f"  U[1] (top) with B[1] (top): U={faces_scrambled['U'][1]}, B={faces_scrambled['B'][1]}")
    print(f"  U[3] (left) with L[1] (top): U={faces_scrambled['U'][3]}, L={faces_scrambled['L'][1]}")  
    print(f"  U[5] (right) with R[1] (top): U={faces_scrambled['U'][5]}, R={faces_scrambled['R'][1]}")
    print(f"  U[7] (bottom) with F[1] (top): U={faces_scrambled['U'][7]}, F={faces_scrambled['F'][1]}")

def test_kociemba_validation():
    """Test what makes kociemba accept or reject a cube"""
    
    # Test 1: All same color (should fail)
    all_u = "U" * 54
    try:
        kociemba.solve(all_u)
        print("✗ All-U cube accepted (unexpected)")
    except:
        print("✓ All-U cube rejected (expected)")
    
    # Test 2: Wrong counts (should fail) 
    wrong_counts = "U" * 10 + "R" * 10 + "F" * 10 + "D" * 10 + "L" * 10 + "B" * 4
    try:
        kociemba.solve(wrong_counts)
        print("✗ Wrong counts accepted (unexpected)")
    except:
        print("✓ Wrong counts rejected (expected)")
        
    # Test 3: Correct counts but impossible arrangement
    impossible = "UUUUUUUUURFRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"  # R in wrong place
    try:
        kociemba.solve(impossible)
        print("✗ Impossible arrangement accepted (unexpected)")
    except:
        print("✓ Impossible arrangement rejected (expected)")

if __name__ == "__main__":
    analyze_valid_cube()
    print("\n" + "="*50)
    test_kociemba_validation()