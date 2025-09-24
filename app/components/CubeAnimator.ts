"use client";
import * as THREE from 'three';

// Types for cube state management
export type CubePosition = [number, number, number];
export type CubeColors = Record<string, string>;

// Animation utilities for Rubik's cube moves
export class CubeAnimator {
  private group: THREE.Group;
  private cubeState: CubeColors[][][];
  private animationSpeed: number = 500; // milliseconds

  constructor(group: THREE.Group, initialState: CubeColors[][][]) {
    this.group = group;
    this.cubeState = this.deepClone(initialState);
  }

  private deepClone(obj: any): any {
    return JSON.parse(JSON.stringify(obj));
  }

  // Get pieces that should rotate for each face
  private getFacePieces(face: string): CubePosition[] {
    const pieces: CubePosition[] = [];
    
    switch (face) {
      case 'U': // Up face (y = 2)
        for (let x = 0; x < 3; x++) {
          for (let z = 0; z < 3; z++) {
            pieces.push([x, 2, z]);
          }
        }
        break;
      case 'D': // Down face (y = 0)
        for (let x = 0; x < 3; x++) {
          for (let z = 0; z < 3; z++) {
            pieces.push([x, 0, z]);
          }
        }
        break;
      case 'R': // Right face (x = 2)
        for (let y = 0; y < 3; y++) {
          for (let z = 0; z < 3; z++) {
            pieces.push([2, y, z]);
          }
        }
        break;
      case 'L': // Left face (x = 0)
        for (let y = 0; y < 3; y++) {
          for (let z = 0; z < 3; z++) {
            pieces.push([0, y, z]);
          }
        }
        break;
      case 'F': // Front face (z = 2)
        for (let x = 0; x < 3; x++) {
          for (let y = 0; y < 3; y++) {
            pieces.push([x, y, 2]);
          }
        }
        break;
      case 'B': // Back face (z = 0)
        for (let x = 0; x < 3; x++) {
          for (let y = 0; y < 3; y++) {
            pieces.push([x, y, 0]);
          }
        }
        break;
    }
    return pieces;
  }

  // Get rotation axis for each face
  private getRotationAxis(face: string): THREE.Vector3 {
    switch (face) {
      case 'U': return new THREE.Vector3(0, 1, 0);  // Y-axis
      case 'D': return new THREE.Vector3(0, -1, 0); // Negative Y-axis
      case 'R': return new THREE.Vector3(1, 0, 0);  // X-axis
      case 'L': return new THREE.Vector3(-1, 0, 0); // Negative X-axis
      case 'F': return new THREE.Vector3(0, 0, 1);  // Z-axis
      case 'B': return new THREE.Vector3(0, 0, -1); // Negative Z-axis
      default: return new THREE.Vector3(0, 1, 0);
    }
  }

  // Get the center point for rotation
  private getRotationCenter(face: string): THREE.Vector3 {
    switch (face) {
      case 'U': return new THREE.Vector3(0, 1.05, 0);  // Up center
      case 'D': return new THREE.Vector3(0, -1.05, 0); // Down center
      case 'R': return new THREE.Vector3(1.05, 0, 0);  // Right center
      case 'L': return new THREE.Vector3(-1.05, 0, 0); // Left center
      case 'F': return new THREE.Vector3(0, 0, 1.05);  // Front center
      case 'B': return new THREE.Vector3(0, 0, -1.05); // Back center
      default: return new THREE.Vector3(0, 0, 0);
    }
  }

  // Animate a single move
  async animateMove(move: string): Promise<void> {
    const face = move[0];
    const modifier = move.slice(1);
    const isCounterClockwise = modifier.includes("'");
    const isDouble = modifier.includes("2");

    // Calculate angle
    let angle = Math.PI / 2; // 90 degrees
    if (isCounterClockwise) angle = -angle;
    if (isDouble) angle *= 2;

    // Get pieces to rotate
    const pieces = this.getFacePieces(face);
    const axis = this.getRotationAxis(face);
    const center = this.getRotationCenter(face);

    // Find the mesh objects to rotate
    const meshesToRotate: THREE.Mesh[] = [];
    pieces.forEach(([x, y, z]) => {
      const position = new THREE.Vector3((x - 1) * 1.05, (y - 1) * 1.05, (z - 1) * 1.05);
      this.group.children.forEach(child => {
        if (child instanceof THREE.Mesh) {
          const meshPos = child.position;
          if (meshPos.distanceTo(position) < 0.1) {
            meshesToRotate.push(child);
          }
        }
      });
    });

    // Create animation
    return new Promise((resolve) => {
      const startTime = Date.now();
      const initialRotations = meshesToRotate.map(mesh => mesh.rotation.clone());
      const initialPositions = meshesToRotate.map(mesh => mesh.position.clone());

      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / this.animationSpeed, 1);
        
        // Easing function for smooth animation
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const currentAngle = angle * easeProgress;

        // Rotate each mesh around the face center
        meshesToRotate.forEach((mesh, index) => {
          const initialPos = initialPositions[index];
          
          // Translate to origin (face center)
          const relativePos = initialPos.clone().sub(center);
          
          // Apply rotation
          const quaternion = new THREE.Quaternion().setFromAxisAngle(axis, currentAngle);
          const rotatedPos = relativePos.clone().applyQuaternion(quaternion);
          
          // Translate back
          mesh.position.copy(rotatedPos.add(center));
          
          // Also rotate the mesh itself
          mesh.rotation.copy(initialRotations[index]);
          mesh.rotateOnWorldAxis(axis, currentAngle);
        });

        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          // Animation complete - update cube state
          this.updateCubeState(face, isCounterClockwise, isDouble);
          resolve();
        }
      };

      animate();
    });
  }

  // Update the internal cube state after a move
  private updateCubeState(face: string, counterClockwise: boolean, double: boolean) {
    // Apply the move to the cube state
    let rotations = 1;
    if (double) rotations = 2;
    
    for (let i = 0; i < rotations; i++) {
      this.rotateFace(face, counterClockwise);
    }
    
    console.log(`Move completed: ${face}${counterClockwise ? "'" : ''}${double ? '2' : ''}`);
  }

  // Rotate a face and its adjacent edges
  private rotateFace(face: string, counterClockwise: boolean = false) {
    switch (face) {
      case 'U':
        this.rotateUpFace(counterClockwise);
        break;
      case 'D':
        this.rotateDownFace(counterClockwise);
        break;
      case 'R':
        this.rotateRightFace(counterClockwise);
        break;
      case 'L':
        this.rotateLeftFace(counterClockwise);
        break;
      case 'F':
        this.rotateFrontFace(counterClockwise);
        break;
      case 'B':
        this.rotateBackFace(counterClockwise);
        break;
    }
  }

  private rotateMatrix3x3(matrix: any[][], counterClockwise: boolean = false) {
    const temp = this.deepClone(matrix);
    
    if (counterClockwise) {
      // Counter-clockwise rotation
      for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
          matrix[2 - j][i] = temp[i][j];
        }
      }
    } else {
      // Clockwise rotation
      for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
          matrix[j][2 - i] = temp[i][j];
        }
      }
    }
  }

  private rotateUpFace(counterClockwise: boolean = false) {
    // Rotate the U face itself
    const uFace = this.cubeState[2].map(row => [...row]);
    this.rotateMatrix3x3(uFace, counterClockwise);
    this.cubeState[2] = uFace;

    // Rotate adjacent edges
    const temp = [
      this.cubeState[0][2][0], this.cubeState[0][2][1], this.cubeState[0][2][2], // Back row
      this.cubeState[1][2][0], this.cubeState[1][2][1], this.cubeState[1][2][2], // Middle row
      this.cubeState[0][2][0], this.cubeState[0][2][1], this.cubeState[0][2][2]  // Front row
    ];

    if (counterClockwise) {
      // L -> F -> R -> B -> L
      [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]] = 
        [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]]; // L <- F
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]]; // F <- R
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = 
        [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]]; // R <- B
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]]; // B <- L
    } else {
      // L -> B -> R -> F -> L
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]]; // B <- L
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = 
        [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]]; // R <- B
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]]; // F <- R
      [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]] = 
        [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]]; // L <- F
    }
  }

  private rotateDownFace(counterClockwise: boolean = false) {
    // Rotate the D face itself
    const dFace = this.cubeState[0].map(row => [...row]);
    this.rotateMatrix3x3(dFace, counterClockwise);
    this.cubeState[0] = dFace;

    // Rotate adjacent edges (opposite to U face)
    if (counterClockwise) {
      // L -> B -> R -> F -> L
      const temp = [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]]; // L
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]]; // L <- B
      [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]] = 
        [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]]; // B <- R
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = 
        [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]]; // R <- F
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = temp; // F <- L
    } else {
      // L -> F -> R -> B -> L
      const temp = [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]]; // L
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]]; // L <- F
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]]; // F <- R
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = 
        [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]]; // R <- B
      [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]] = temp; // B <- L
    }
  }

  private rotateRightFace(counterClockwise: boolean = false) {
    // Rotate the R face colors by rotating the slice at x=2
    const rFace: CubeColors[][] = [];
    for (let y = 0; y < 3; y++) {
      rFace[y] = [];
      for (let z = 0; z < 3; z++) {
        rFace[y][z] = this.cubeState[y][z][2];
      }
    }
    this.rotateMatrix3x3(rFace, counterClockwise);
    for (let y = 0; y < 3; y++) {
      for (let z = 0; z < 3; z++) {
        this.cubeState[y][z][2] = rFace[y][z];
      }
    }

    // Rotate adjacent edges: U -> B -> D -> F -> U
    if (counterClockwise) {
      const temp = [this.cubeState[2][0][2], this.cubeState[2][1][2], this.cubeState[2][2][2]]; // U
      [this.cubeState[2][0][2], this.cubeState[2][1][2], this.cubeState[2][2][2]] = 
        [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]]; // U <- F
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [this.cubeState[0][0][2], this.cubeState[0][1][2], this.cubeState[0][2][2]]; // F <- D
      [this.cubeState[0][0][2], this.cubeState[0][1][2], this.cubeState[0][2][2]] = 
        [this.cubeState[2][0][0], this.cubeState[1][0][0], this.cubeState[0][0][0]]; // D <- B (reversed)
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [temp[2], temp[1], temp[0]]; // B <- U (reversed)
    } else {
      const temp = [this.cubeState[2][0][2], this.cubeState[2][1][2], this.cubeState[2][2][2]]; // U
      [this.cubeState[2][0][2], this.cubeState[2][1][2], this.cubeState[2][2][2]] = 
        [this.cubeState[2][0][0], this.cubeState[1][0][0], this.cubeState[0][0][0]]; // U <- B (reversed)
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [this.cubeState[0][2][2], this.cubeState[0][1][2], this.cubeState[0][0][2]]; // B <- D (reversed)
      [this.cubeState[0][0][2], this.cubeState[0][1][2], this.cubeState[0][2][2]] = 
        [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]]; // D <- F
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = temp; // F <- U
    }
  }

  private rotateLeftFace(counterClockwise: boolean = false) {
    // Rotate the L face colors
    const lFace: CubeColors[][] = [];
    for (let y = 0; y < 3; y++) {
      lFace[y] = [];
      for (let z = 0; z < 3; z++) {
        lFace[y][z] = this.cubeState[y][z][0];
      }
    }
    this.rotateMatrix3x3(lFace, counterClockwise);
    for (let y = 0; y < 3; y++) {
      for (let z = 0; z < 3; z++) {
        this.cubeState[y][z][0] = lFace[y][z];
      }
    }

    // Rotate adjacent edges (opposite to R face)
    if (counterClockwise) {
      const temp = [this.cubeState[2][0][0], this.cubeState[2][1][0], this.cubeState[2][2][0]]; // U
      [this.cubeState[2][0][0], this.cubeState[2][1][0], this.cubeState[2][2][0]] = 
        [this.cubeState[2][2][2], this.cubeState[1][2][2], this.cubeState[0][2][2]]; // U <- B (reversed)
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = 
        [this.cubeState[0][2][0], this.cubeState[0][1][0], this.cubeState[0][0][0]]; // B <- D (reversed)
      [this.cubeState[0][0][0], this.cubeState[0][1][0], this.cubeState[0][2][0]] = 
        [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]]; // D <- F
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = temp; // F <- U
    } else {
      const temp = [this.cubeState[2][0][0], this.cubeState[2][1][0], this.cubeState[2][2][0]]; // U
      [this.cubeState[2][0][0], this.cubeState[2][1][0], this.cubeState[2][2][0]] = 
        [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]]; // U <- F
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = 
        [this.cubeState[0][0][0], this.cubeState[0][1][0], this.cubeState[0][2][0]]; // F <- D
      [this.cubeState[0][0][0], this.cubeState[0][1][0], this.cubeState[0][2][0]] = 
        [this.cubeState[2][2][2], this.cubeState[1][2][2], this.cubeState[0][2][2]]; // D <- B (reversed)
      [this.cubeState[0][2][2], this.cubeState[1][2][2], this.cubeState[2][2][2]] = 
        [temp[2], temp[1], temp[0]]; // B <- U (reversed)
    }
  }

  private rotateFrontFace(counterClockwise: boolean = false) {
    // Rotate the F face itself
    const fFace: CubeColors[][] = [];
    for (let x = 0; x < 3; x++) {
      fFace[x] = [];
      for (let y = 0; y < 3; y++) {
        fFace[x][y] = this.cubeState[y][x][2];
      }
    }
    this.rotateMatrix3x3(fFace, counterClockwise);
    for (let x = 0; x < 3; x++) {
      for (let y = 0; y < 3; y++) {
        this.cubeState[y][x][2] = fFace[x][y];
      }
    }

    // Rotate adjacent edges: U -> R -> D -> L -> U
    if (counterClockwise) {
      const temp = [this.cubeState[2][2][0], this.cubeState[2][2][1], this.cubeState[2][2][2]]; // U bottom edge
      [this.cubeState[2][2][0], this.cubeState[2][2][1], this.cubeState[2][2][2]] = 
        [this.cubeState[2][0][2], this.cubeState[1][0][2], this.cubeState[0][0][2]]; // U <- R (rotated)
      [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]] = 
        [this.cubeState[0][2][2], this.cubeState[0][2][1], this.cubeState[0][2][0]]; // R <- D (rotated)
      [this.cubeState[0][2][0], this.cubeState[0][2][1], this.cubeState[0][2][2]] = 
        [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]]; // D <- L
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [temp[2], temp[1], temp[0]]; // L <- U (rotated)
    } else {
      const temp = [this.cubeState[2][2][0], this.cubeState[2][2][1], this.cubeState[2][2][2]]; // U bottom edge
      [this.cubeState[2][2][0], this.cubeState[2][2][1], this.cubeState[2][2][2]] = 
        [this.cubeState[2][2][0], this.cubeState[1][2][0], this.cubeState[0][2][0]]; // U <- L
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [this.cubeState[0][2][0], this.cubeState[0][2][1], this.cubeState[0][2][2]]; // L <- D
      [this.cubeState[0][2][0], this.cubeState[0][2][1], this.cubeState[0][2][2]] = 
        [this.cubeState[2][0][2], this.cubeState[1][0][2], this.cubeState[0][0][2]]; // D <- R (rotated)
      [this.cubeState[0][0][2], this.cubeState[1][0][2], this.cubeState[2][0][2]] = 
        [temp[2], temp[1], temp[0]]; // R <- U (rotated)
    }
  }

  private rotateBackFace(counterClockwise: boolean = false) {
    // Rotate the B face itself
    const bFace: CubeColors[][] = [];
    for (let x = 0; x < 3; x++) {
      bFace[x] = [];
      for (let y = 0; y < 3; y++) {
        bFace[x][y] = this.cubeState[y][x][0];
      }
    }
    this.rotateMatrix3x3(bFace, counterClockwise);
    for (let x = 0; x < 3; x++) {
      for (let y = 0; y < 3; y++) {
        this.cubeState[y][x][0] = bFace[x][y];
      }
    }

    // Rotate adjacent edges (opposite to F face)
    if (counterClockwise) {
      const temp = [this.cubeState[2][0][0], this.cubeState[2][0][1], this.cubeState[2][0][2]]; // U top edge
      [this.cubeState[2][0][0], this.cubeState[2][0][1], this.cubeState[2][0][2]] = 
        [this.cubeState[2][2][0], this.cubeState[1][2][0], this.cubeState[0][2][0]]; // U <- L (rotated)
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [this.cubeState[0][0][2], this.cubeState[0][0][1], this.cubeState[0][0][0]]; // L <- D (rotated)
      [this.cubeState[0][0][0], this.cubeState[0][0][1], this.cubeState[0][0][2]] = 
        [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]]; // D <- R
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [temp[2], temp[1], temp[0]]; // R <- U (rotated)
    } else {
      const temp = [this.cubeState[2][0][0], this.cubeState[2][0][1], this.cubeState[2][0][2]]; // U top edge
      [this.cubeState[2][0][0], this.cubeState[2][0][1], this.cubeState[2][0][2]] = 
        [this.cubeState[2][0][0], this.cubeState[1][0][0], this.cubeState[0][0][0]]; // U <- R
      [this.cubeState[0][0][0], this.cubeState[1][0][0], this.cubeState[2][0][0]] = 
        [this.cubeState[0][0][0], this.cubeState[0][0][1], this.cubeState[0][0][2]]; // R <- D
      [this.cubeState[0][0][0], this.cubeState[0][0][1], this.cubeState[0][0][2]] = 
        [this.cubeState[2][2][0], this.cubeState[1][2][0], this.cubeState[0][2][0]]; // D <- L (rotated)
      [this.cubeState[0][2][0], this.cubeState[1][2][0], this.cubeState[2][2][0]] = 
        [temp[2], temp[1], temp[0]]; // L <- U (rotated)
    }
  }

  // Reset cube to initial state
  reset(initialState: CubeColors[][][]) {
    this.cubeState = this.deepClone(initialState);
    
    // Reset all mesh positions and rotations
    this.group.children.forEach((child, index) => {
      if (child instanceof THREE.Mesh) {
        const x = Math.floor(index / 9);
        const y = Math.floor((index % 9) / 3);
        const z = index % 3;
        
        child.position.set((x - 1) * 1.05, (y - 1) * 1.05, (z - 1) * 1.05);
        child.rotation.set(0, 0, 0);
      }
    });
  }

  // Set animation speed
  setSpeed(speedMs: number) {
    this.animationSpeed = speedMs;
  }

  // Get current cube state
  getCubeState(): CubeColors[][][] {
    return this.deepClone(this.cubeState);
  }

  // Update cube state (for external synchronization)
  updateState(newState: CubeColors[][][]) {
    this.cubeState = this.deepClone(newState);
  }
}

// Utility functions for move parsing and validation
export function parseMove(move: string): { face: string; clockwise: boolean; double: boolean } {
  const face = move[0];
  const modifier = move.slice(1);
  
  return {
    face,
    clockwise: !modifier.includes("'"),
    double: modifier.includes("2")
  };
}

export function validateMove(move: string): boolean {
  const validFaces = ['U', 'D', 'R', 'L', 'F', 'B'];
  const face = move[0];
  const modifier = move.slice(1);
  
  if (!validFaces.includes(face)) return false;
  if (modifier && !["'", "2", "'2", "2'"].includes(modifier)) return false;
  
  return true;
}

export function describeMoveDetailed(move: string): string {
  const { face, clockwise, double } = parseMove(move);
  
  const faceNames: Record<string, string> = {
    'U': 'Upper',
    'D': 'Down',
    'R': 'Right', 
    'L': 'Left',
    'F': 'Front',
    'B': 'Back'
  };
  
  const faceName = faceNames[face] || face;
  const direction = clockwise ? 'clockwise' : 'counter-clockwise';
  const amount = double ? '180°' : '90°';
  
  return `Turn ${faceName} face ${amount} ${direction}`;
}