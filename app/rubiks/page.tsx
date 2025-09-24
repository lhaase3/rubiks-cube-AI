
"use client";
import React, { useEffect, useRef, useState } from "react";
import dynamic from 'next/dynamic';

// Dynamically import the CubeViewer to avoid SSR issues with Three.js
const CubeViewer = dynamic(() => import('../components/CubeViewer'), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-[400px] bg-neutral-900 border border-neutral-700 rounded-xl flex items-center justify-center">
      <div className="text-neutral-400">Loading 3D viewer...</div>
    </div>
  )
});

const FACE_ORDER = ["U","R","F","D","L","B"] as const;
type Face = typeof FACE_ORDER[number];

type FaceData = {
  file?: File;
  preview?: string;
};

export default function RubiksPage() {
  const [faces, setFaces] = useState<Record<Face, FaceData>>({
    U: {}, R: {}, F: {}, D: {}, L: {}, B: {}
  });
  const [activeCamFace, setActiveCamFace] = useState<Face | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [solving, setSolving] = useState(false);
  const [moves, setMoves] = useState<string[]>([]);
  const [error, setError] = useState<string>("");
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1);
  const [debugMode, setDebugMode] = useState(false);
  const [debugData, setDebugData] = useState<any>(null);
  const [initialCubeState, setInitialCubeState] = useState<string>("");

  const SOLVER_URL = process.env.NEXT_PUBLIC_SOLVER_URL || "http://localhost:5001/solve";
  const DEBUG_URL = process.env.NEXT_PUBLIC_DEBUG_URL || "http://localhost:5001/debug-colors";

  // Debug logging for state changes
  useEffect(() => {
    console.log("initialCubeState changed to:", initialCubeState);
  }, [initialCubeState]);

  // Start/stop webcam when modal opens/closes
  useEffect(() => {
    (async () => {
      if (activeCamFace && videoRef.current) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
          streamRef.current = stream;
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        } catch (e) {
          console.error(e);
          setError("Could not access webcam. Check permission settings.");
        }
      } else {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t: MediaStreamTrack) => t.stop());
          streamRef.current = null;
        }
      }
    })();
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach((t: MediaStreamTrack) => t.stop());
    };
  }, [activeCamFace]);

  const onFile = (face: Face, f?: File) => {
    setError("");
    if (!f) return;
    const url = URL.createObjectURL(f);
    setFaces((prev: Record<Face, FaceData>) => ({ ...prev, [face]: { file: f, preview: url } }));
  };

  const captureFromWebcam = async () => {
    if (!activeCamFace || !videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>(res => canvas.toBlob(b => res(b), "image/jpeg", 0.92));
    if (!blob) return;
    const file = new File([blob], `${activeCamFace}.jpg`, { type: "image/jpeg" });
    const url = URL.createObjectURL(file);
    setFaces((prev: Record<Face, FaceData>) => ({ ...prev, [activeCamFace]: { file, preview: url } }));
    setActiveCamFace(null);
  };

  const allSet = FACE_ORDER.every(f => faces[f].file);

  const debugColors = async () => {
    if (!allSet) { 
      setError("Please provide all 6 faces first."); 
      return; 
    }
    
    setError(""); 
    setDebugData(null);
    
    const fd = new FormData();
    FACE_ORDER.forEach(face => { 
      if (faces[face].file) fd.append(face, faces[face].file as File); 
    });
    
    try {
      const resp = await fetch(DEBUG_URL, { method: "POST", body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setDebugData(data);
      setDebugMode(true);
    } catch (e: any) {
      console.error(e);
      setError(e?.message || "Debug failed");
    }
  };

  const testCube = async () => {
    try {
      console.log("Test cube button clicked!");
      const resp = await fetch("http://localhost:5001/test-cube");
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      console.log("Test cube response:", data);
      alert(`Test cube response: ${JSON.stringify(data).slice(0, 100)}...`);
      setMoves(data.moves || []);
      setInitialCubeState(data.cube_string || data.initial_state || "");
      console.log("Set initialCubeState to:", data.cube_string || data.initial_state);
      setError("");
    } catch (e: any) {
      console.error(e);
      setError(e?.message || "Test failed");
    }
  };

  const submit = async () => {
    if (!allSet) { setError("Please provide all 6 faces (U, R, F, D, L, B)."); return; }
    setSolving(true); setError(""); setMoves([]); setInitialCubeState("");
    const fd = new FormData();
    FACE_ORDER.forEach(face => { if (faces[face].file) fd.append(face, faces[face].file as File); });
    try {
      const resp = await fetch(SOLVER_URL, { method: "POST", body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setMoves(data.moves || []);
      setInitialCubeState(data.initial_state || "");
    } catch (e: any) {
      console.error(e);
      setError(e?.message || "Solve failed");
    } finally {
      setSolving(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 p-6">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-semibold tracking-tight">Rubik’s Cube Solver</h1>
        <p className="text-neutral-400 mt-1">Upload or capture each face (U, R, F, D, L, B), then click Solve.</p>

        {/* Face grid */}
        <div className="grid md:grid-cols-3 gap-5 mt-6">
          {FACE_ORDER.map(face => (
            <div key={face} className="rounded-2xl border border-neutral-800 p-4 bg-neutral-900/50">
              <div className="flex items-center justify-between mb-3">
                <div className="font-medium">{face}</div>
                <div className="text-xs text-neutral-400">Upload or Camera</div>
              </div>

              <div className="aspect-video rounded-xl overflow-hidden bg-neutral-800 flex items-center justify-center">
                {faces[face].preview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={faces[face].preview} alt={`${face} preview`} className="w-full h-full object-contain" />
                ) : (
                  <div className="text-neutral-500 text-sm">No image yet</div>
                )}
              </div>

              <div className="flex items-center gap-3 mt-3">
                <label className="cursor-pointer text-sm px-3 py-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 border border-neutral-700">
                  Upload
                  <input type="file" accept="image/*" className="hidden" onChange={(e: React.ChangeEvent<HTMLInputElement>) => onFile(face, e.target.files?.[0])} />
                </label>
                <button className="text-sm px-3 py-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 border border-neutral-700"
                        onClick={() => setActiveCamFace(face)}>Use Camera</button>
                {faces[face].file && (
                  <button className="text-sm px-3 py-2 rounded-lg border border-red-500/40 text-red-300 hover:bg-red-900/30"
                          onClick={() => setFaces((prev: Record<Face, FaceData>) => ({...prev, [face]: {}}))}>Clear</button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="mt-6 flex items-center gap-4 flex-wrap">
          <button onClick={submit}
                  disabled={!allSet || solving}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700">
            {solving ? "Solving…" : "Solve"}
          </button>
          <button onClick={debugColors}
                  disabled={!allSet}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-700">
            Debug Colors
          </button>
          <button onClick={testCube}
                  className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500">
            Test Cube
          </button>
          {!allSet && <span className="text-sm text-neutral-400">Need all 6 faces</span>}
          {error && <span className="text-sm text-red-400">{error}</span>}
        </div>

        {/* Debug Results */}
        {debugMode && debugData && (
          <div className="mt-8 rounded-2xl border border-neutral-800 p-4 bg-neutral-900/50">
            <div className="flex items-center justify-between mb-4">
              <div className="font-medium">Color Detection Analysis</div>
              <button onClick={() => setDebugMode(false)} className="text-neutral-400 hover:text-white">✕</button>
            </div>

            {/* Overall Statistics */}
            <div className="mb-4 p-3 rounded-lg bg-neutral-800/50">
              <div className="font-medium mb-2">Overall Statistics</div>
              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <div>Status: <span className={debugData.status === 'success' ? 'text-green-400' : 'text-yellow-400'}>{debugData.status}</span></div>
                <div>Average Confidence: <span className="font-mono">{debugData.overall_statistics?.average_confidence || 'N/A'}</span></div>
                <div>Correct Color Counts: <span className="font-mono">{debugData.overall_statistics?.colors_with_correct_count || 0}/6</span></div>
                <div>Correct Center Colors: <span className="font-mono">{debugData.overall_statistics?.faces_with_correct_center || 0}/6</span></div>
              </div>
            </div>

            {/* Recommendations */}
            {debugData.recommendations && debugData.recommendations.length > 0 && (
              <div className="mb-4 p-3 rounded-lg bg-blue-900/30 border border-blue-500/30">
                <div className="font-medium mb-2 text-blue-300">Recommendations</div>
                <ul className="text-sm space-y-1">
                  {debugData.recommendations.map((rec: string, i: number) => (
                    <li key={i} className="text-blue-200">• {rec}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Color Counts */}
            <div className="mb-4 p-3 rounded-lg bg-neutral-800/50">
              <div className="font-medium mb-2">Color Distribution</div>
              <div className="grid grid-cols-6 gap-2 text-sm">
                {FACE_ORDER.map(face => (
                  <div key={face} className={`text-center p-2 rounded ${(debugData.total_counts?.[face] || 0) === 9 ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'}`}>
                    <div className="font-mono font-bold">{face}</div>
                    <div>{debugData.total_counts?.[face] || 0}/9</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Detailed Face Analysis */}
            <div className="space-y-3">
              {FACE_ORDER.map(face => (
                <details key={face} className="group">
                  <summary className="cursor-pointer p-3 rounded-lg bg-neutral-800/50 hover:bg-neutral-800 group-open:rounded-b-none">
                    <span className="font-medium">{face} Face Analysis</span>
                    <span className={`ml-2 text-sm ${debugData.face_statistics?.[face]?.center_matches_face ? 'text-green-400' : 'text-red-400'}`}>
                      (Center: {debugData.face_statistics?.[face]?.center_color || 'N/A'}, 
                      Confidence: {debugData.face_statistics?.[face]?.average_confidence || 'N/A'})
                    </span>
                  </summary>
                  <div className="p-3 bg-neutral-800/30 rounded-b-lg">
                    <div className="grid grid-cols-3 gap-1 mb-3">
                      {(debugData.color_analysis?.[face] || []).map((tile: any, i: number) => (
                        <div key={i} className={`p-2 text-xs text-center rounded border ${i === 4 ? 'border-yellow-500' : 'border-neutral-600'}`}>
                          <div className="font-mono font-bold">{tile.detected_color || 'N/A'}</div>
                          <div className="text-neutral-400">conf: {tile.confidence || 'N/A'}</div>
                        </div>
                      ))}
                    </div>
                    <div className="text-xs text-neutral-400">
                      Unique colors: {debugData.face_statistics?.[face]?.unique_colors?.join(', ') || 'N/A'}
                    </div>
                  </div>
                </details>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {(moves.length > 0 || initialCubeState) && (
          <div className="mt-8 space-y-6">
            {/* 3D Animation */}
            <div className="rounded-2xl border border-neutral-800 p-4 bg-neutral-900/50">
              <div className="font-medium mb-4">
                3D Cube Solver Animation
                <div className="text-xs text-neutral-400 mt-1">
                  Current state: {initialCubeState ? `"${initialCubeState.slice(0, 20)}..."` : "No cube state"}
                </div>
              </div>
              
              {/* 3D Cube Viewer */}
              <div className="h-[500px]">
                <CubeViewer 
                  key={`cube-${initialCubeState}`} // Force complete re-render when cube state changes
                  moves={moves} 
                  onMoveChange={(moveIndex) => setCurrentMoveIndex(moveIndex)}
                  initialCubeState={initialCubeState}
                />
              </div>
            </div>

            {/* Move List */}
            <div className="rounded-2xl border border-neutral-800 p-4 bg-neutral-900/50">
              <div className="font-medium mb-2">Solution Steps ({moves.length} moves)</div>
              <div className="text-sm text-neutral-400 mb-4">
                Click on any move below to jump to that step in the animation
              </div>
              <ol className="list-decimal ml-6 grid md:grid-cols-2 gap-x-8">
                {moves.map((m, i) => (
                  <li 
                    key={i} 
                    className={`py-2 cursor-pointer rounded px-3 -mx-3 transition-colors hover:bg-neutral-800/50 ${
                      i === currentMoveIndex ? 'bg-emerald-900/50 text-emerald-300 border-l-2 border-emerald-500' : 
                      i < currentMoveIndex ? 'text-neutral-500' : ''
                    }`}
                    onClick={() => setCurrentMoveIndex(i)}
                  >
                    <span className="inline-block w-10 font-mono font-bold">{m}</span>
                    <span className="text-neutral-400 ml-3">{describeMove(m)}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </div>

      {/* Webcam modal */}
      {activeCamFace && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-4 w-full max-w-3xl">
            <div className="flex items-center justify-between mb-2">
              <div className="font-medium">Capture {activeCamFace}</div>
              <button onClick={() => setActiveCamFace(null)} className="text-neutral-400 hover:text-white">✕</button>
            </div>
            <div className="relative">
              <video ref={videoRef} className="w-full rounded-xl border border-neutral-800" playsInline muted></video>
              {/* simple 3×3 guide overlay */}
              <div className="pointer-events-none absolute inset-0 grid grid-cols-3 grid-rows-3">
                {Array.from({length: 9}).map((_, i) => (
                  <div key={i} className="border border-emerald-400/40" />
                ))}
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 mt-3">
              <button onClick={() => setActiveCamFace(null)} className="px-3 py-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 border border-neutral-700">Cancel</button>
              <button onClick={captureFromWebcam} className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500">Capture</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function describeMove(token: string) {
  const face = token[0];
  const suf = token.slice(1);
  const base: Record<string, string> = {
    U: "Turn the Up face clockwise",
    D: "Turn the Down face clockwise",
    L: "Turn the Left face clockwise",
    R: "Turn the Right face clockwise",
    F: "Turn the Front face clockwise",
    B: "Turn the Back face clockwise",
  };
  let txt = base[face] || token;
  if (suf === "'") txt = txt.replace("clockwise", "counter-clockwise");
  if (suf === "2") txt = txt.replace("clockwise", "180°");
  return txt;
}
