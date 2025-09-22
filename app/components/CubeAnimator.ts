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
    // This is a simplified state update - in a full implementation,
    // you would need to properly track the color state changes
    // For now, we'll just mark that the move was completed
    console.log(`Move completed: ${face}${counterClockwise ? "'" : ''}${double ? '2' : ''}`);
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