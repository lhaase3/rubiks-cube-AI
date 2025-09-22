"use client";
import React, { useRef, useMemo, useState, useImperativeHandle, forwardRef, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { CubeAnimator, validateMove, describeMoveDetailed } from './CubeAnimator';

// Face colors for a standard Rubik's cube
const FACE_COLORS = {
  U: '#ffffff', // White - Up
  D: '#ffff00', // Yellow - Down  
  F: '#00ff00', // Green - Front
  B: '#0000ff', // Blue - Back
  R: '#ff0000', // Red - Right
  L: '#ffa500', // Orange - Left
};

// Individual cube piece component
function CubePiece({ position, colors }: { position: [number, number, number], colors: Record<string, string> }) {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Create materials for each face
  const materials = useMemo(() => {
    return [
      new THREE.MeshLambertMaterial({ color: colors.R || '#000000' }), // Right (+X)
      new THREE.MeshLambertMaterial({ color: colors.L || '#000000' }), // Left (-X)
      new THREE.MeshLambertMaterial({ color: colors.U || '#000000' }), // Top (+Y)
      new THREE.MeshLambertMaterial({ color: colors.D || '#000000' }), // Bottom (-Y)
      new THREE.MeshLambertMaterial({ color: colors.F || '#000000' }), // Front (+Z)
      new THREE.MeshLambertMaterial({ color: colors.B || '#000000' }), // Back (-Z)
    ];
  }, [colors]);

  return (
    <mesh ref={meshRef} position={position}>
      <boxGeometry args={[0.95, 0.95, 0.95]} />
      {materials.map((material, index) => (
        <primitive key={index} object={material} attach={`material-${index}`} />
      ))}
    </mesh>
  );
}

// Main cube component that can be controlled externally
export interface CubeRef {
  animateMove: (move: string) => Promise<void>;
  reset: () => void;
}

const RubiksCube = forwardRef<CubeRef>((props, ref) => {
  const groupRef = useRef<THREE.Group>(null);
  const [cubeState, setCubeState] = useState<Record<string, string>[][][]>(() => initializeCube());
  const [isAnimating, setIsAnimating] = useState(false);
  const animatorRef = useRef<CubeAnimator | null>(null);

  // Initialize animator when group is ready
  useEffect(() => {
    if (groupRef.current && !animatorRef.current) {
      animatorRef.current = new CubeAnimator(groupRef.current, cubeState);
    }
  }, [cubeState]);

  function initializeCube(): Record<string, string>[][][] {
    const cube: Record<string, string>[][][] = [];
    for (let x = 0; x < 3; x++) {
      cube[x] = [];
      for (let y = 0; y < 3; y++) {
        cube[x][y] = [];
        for (let z = 0; z < 3; z++) {
          const colors: Record<string, string> = {};
          
          // Only show colors on outer faces
          if (x === 0) colors.L = FACE_COLORS.L; // Left face
          if (x === 2) colors.R = FACE_COLORS.R; // Right face
          if (y === 0) colors.D = FACE_COLORS.D; // Down face
          if (y === 2) colors.U = FACE_COLORS.U; // Up face
          if (z === 0) colors.B = FACE_COLORS.B; // Back face
          if (z === 2) colors.F = FACE_COLORS.F; // Front face
          
          cube[x][y][z] = colors;
        }
      }
    }
    return cube;
  }

  const animateMove = async (move: string): Promise<void> => {
    if (isAnimating || !animatorRef.current) return;
    if (!validateMove(move)) {
      console.warn('Invalid move:', move);
      return;
    }
    
    setIsAnimating(true);
    
    try {
      await animatorRef.current.animateMove(move);
    } catch (error) {
      console.error('Animation error:', error);
    } finally {
      setIsAnimating(false);
    }
  };

  const reset = () => {
    if (animatorRef.current) {
      const initialState = initializeCube();
      setCubeState(initialState);
      animatorRef.current.reset(initialState);
    }
    setIsAnimating(false);
  };

  useImperativeHandle(ref, () => ({
    animateMove,
    reset
  }));

  // Slow auto-rotation when not animating
  useFrame((state) => {
    if (groupRef.current && !isAnimating) {
      groupRef.current.rotation.y += 0.003;
    }
  });

  return (
    <group ref={groupRef}>
      {cubeState.map((xLayer, x) =>
        xLayer.map((yLayer, y) =>
          yLayer.map((colors, z) => (
            <CubePiece
              key={`${x}-${y}-${z}`}
              position={[(x - 1) * 1.05, (y - 1) * 1.05, (z - 1) * 1.05]}
              colors={colors}
            />
          ))
        )
      )}
    </group>
  );
});

RubiksCube.displayName = 'RubiksCube';

// Scene component with lighting and camera
function CubeScene({ cubeRef }: { cubeRef: React.RefObject<CubeRef> }) {
  return (
    <>
      {/* Enhanced lighting setup */}
      <ambientLight intensity={0.3} />
      <directionalLight position={[10, 10, 5]} intensity={1.0} castShadow />
      <directionalLight position={[-10, -10, -5]} intensity={0.4} />
      <directionalLight position={[0, 10, 0]} intensity={0.3} />
      <pointLight position={[5, 5, 5]} intensity={0.5} />
      
      {/* Camera controls with better defaults */}
      <OrbitControls 
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={6}
        maxDistance={15}
        autoRotate={false}
        dampingFactor={0.05}
        enableDamping={true}
        rotateSpeed={0.5}
        zoomSpeed={0.8}
        panSpeed={0.8}
      />
      
      {/* The cube */}
      <RubiksCube ref={cubeRef} />
      
      {/* Background gradient effect */}
      <mesh position={[0, 0, -8]} scale={20}>
        <planeGeometry />
        <meshBasicMaterial color="#1a1a1a" transparent opacity={0.1} />
      </mesh>
    </>
  );
}

// Main component that wraps everything
export default function CubeViewer({ 
  moves = [], 
  onMoveChange 
}: { 
  moves?: string[]; 
  onMoveChange?: (currentMove: number) => void;
}) {
  const cubeRef = useRef<CubeRef>(null);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);

  const playMove = async (moveIndex: number) => {
    if (moveIndex >= moves.length || !cubeRef.current) return;
    
    await cubeRef.current.animateMove(moves[moveIndex]);
    setCurrentMoveIndex(moveIndex);
    onMoveChange?.(moveIndex);
  };

  const playAllMoves = async () => {
    if (isPlaying || !cubeRef.current) return;
    
    setIsPlaying(true);
    cubeRef.current.reset();
    setCurrentMoveIndex(-1);
    
    for (let i = 0; i < moves.length; i++) {
      await playMove(i);
      await new Promise(resolve => setTimeout(resolve, 600)); // Pause between moves
    }
    
    setIsPlaying(false);
  };

  const resetCube = () => {
    if (cubeRef.current) {
      cubeRef.current.reset();
      setCurrentMoveIndex(-1);
      setIsPlaying(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* 3D Viewer */}
      <div className="flex-1 min-h-[400px] border border-neutral-700 rounded-xl overflow-hidden bg-gradient-to-br from-neutral-900 via-neutral-800 to-neutral-900 shadow-2xl">
        <Canvas
          camera={{ position: [7, 7, 7], fov: 45 }}
          gl={{ antialias: true, alpha: true }}
          shadows
        >
          <CubeScene cubeRef={cubeRef} />
        </Canvas>
      </div>
      
      {/* Controls */}
      {moves.length > 0 && (
        <div className="mt-4 p-4 bg-neutral-900/50 rounded-xl border border-neutral-800">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium">Animation Controls</h3>
            <div className="text-sm text-neutral-400">
              Move {currentMoveIndex + 1} of {moves.length}
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={playAllMoves}
              disabled={isPlaying}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 rounded-lg text-sm font-medium"
            >
              {isPlaying ? 'Playing...' : 'Play All'}
            </button>
            
            <button
              onClick={resetCube}
              disabled={isPlaying}
              className="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 disabled:bg-neutral-800 rounded-lg text-sm"
            >
              Reset
            </button>
            
            <div className="text-center">
              {currentMoveIndex >= 0 && (
                <div className="text-sm">
                  <div className="font-mono font-bold text-emerald-400 text-lg mb-1">
                    {moves[currentMoveIndex]}
                  </div>
                  <div className="text-neutral-400 text-xs">
                    {describeMoveDetailed(moves[currentMoveIndex])}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Move list */}
          <div className="mt-3 max-h-24 overflow-y-auto">
            <div className="flex flex-wrap gap-1">
              {moves.map((move, index) => (
                <button
                  key={index}
                  onClick={() => !isPlaying && playMove(index)}
                  disabled={isPlaying}
                  className={`px-2 py-1 text-xs rounded font-mono ${
                    index === currentMoveIndex
                      ? 'bg-emerald-600 text-white'
                      : index < currentMoveIndex
                      ? 'bg-emerald-900/50 text-emerald-300'
                      : 'bg-neutral-700 text-neutral-300 hover:bg-neutral-600'
                  } disabled:opacity-50`}
                >
                  {move}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}