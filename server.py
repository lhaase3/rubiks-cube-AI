import os
from itertools import product

from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2 as cv
import numpy as np
import kociemba

# ----------------------------
# Config
# ----------------------------
FACE_ORDER = ["U", "R", "F", "D", "L", "B"]
PORT = int(os.environ.get("PORT", 5001))

app = Flask(__name__)
CORS(app)  # allow localhost frontend

# ----------------------------
# Orientation helpers (sampled)
# ----------------------------
ROT_X = str.maketrans({"U": "B", "B": "D", "D": "F", "F": "U", "R": "R", "L": "L"})
ROT_Y = str.maketrans({"F": "R", "R": "B", "B": "L", "L": "F", "U": "U", "D": "D"})
ROT_Z = str.maketrans({"U": "R", "R": "D", "D": "L", "L": "U", "F": "F", "B": "B"})

def _compose_tables(a, b):
    """Compose two maketrans tables for face relabeling."""
    ad = {chr(k): chr(v) for k, v in a.items()}
    bd = {chr(k): chr(v) for k, v in b.items()}
    out = {}
    for ch in "URFDLB":
        mid = bd.get(ch, ch)
        out[ch] = ad.get(mid, mid)
    return {ord(k): ord(v) for k, v in out.items()}

def _rotations_sample(n=12):
    """Return ~n orientation relabelings (subset of 24) to shave a few moves quickly."""
    base = {ord(c): ord(c) for c in "URFDLB"}
    R = []
    seen = set()
    for x, y, z in product(range(4), range(3), range(4)):
        t = base
        for _ in range(x):
            t = _compose_tables(ROT_X, t)
        for _ in range(y):
            t = _compose_tables(ROT_Y, t)
        for _ in range(z):
            t = _compose_tables(ROT_Z, t)
        key = tuple((k, t[k]) for k in sorted(t.keys()))
        if key not in seen:
            seen.add(key)
            R.append(t)
        if len(R) >= n:
            break
    return R

def _invert_table(t):
    return {v: k for k, v in t.items()}

def _relabel_moves(moves_str, inverse_table):
    inv = _invert_table(inverse_table)
    out = []
    for tok in moves_str.split():
        face, suf = tok[0], tok[1:]
        back = chr(inv.get(ord(face), ord(face)))
        out.append(back + suf)
    return " ".join(out)

# ----------------------------
# OpenCV helpers
# ----------------------------
def _circular_hue_delta(h1, h2):
    d = abs(h1 - h2)
    return min(d, 180 - d)  # cv Hue range is [0..180]

def _hsv_mean_center_patch(img_bgr, patch_frac=0.4):
    h, w = img_bgr.shape[:2]
    ph, pw = int(h * patch_frac), int(w * patch_frac)
    y0 = (h - ph) // 2
    x0 = (w - pw) // 2
    patch = img_bgr[y0:y0 + ph, x0:x0 + pw]
    hsv = cv.cvtColor(patch, cv.COLOR_BGR2HSV)
    return np.mean(hsv.reshape(-1, 3), axis=0)  # [H, S, V]

def _find_face_warp(img_bgr, out_size=600):
    """Find a quadrilateral (face) and warp to a square. Fallback: use full frame."""
    gray = cv.cvtColor(img_bgr, cv.COLOR_BGR2GRAY)
    blur = cv.GaussianBlur(gray, (5, 5), 0)
    edges = cv.Canny(blur, 50, 150)
    cnts, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    if not cnts:
        h, w = img_bgr.shape[:2]
        approx = np.array([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]], dtype=np.int32)
    else:
        c = max(cnts, key=cv.contourArea)
        peri = cv.arcLength(c, True)
        approx = cv.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            h, w = img_bgr.shape[:2]
            approx = np.array([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]], dtype=np.int32)

    pts = approx.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    dst = np.array([[0, 0], [out_size, 0], [out_size, out_size], [0, out_size]], dtype=np.float32)
    M = cv.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype=np.float32), dst)
    return cv.warpPerspective(img_bgr, M, (out_size, out_size))

def _slice_face_into_9(warped):
    H, W = warped.shape[:2]
    h, w = H // 3, W // 3
    return [warped[r * h:(r + 1) * h, c * w:(c + 1) * w] for r in range(3) for c in range(3)]

# ----------------------------
# Color calibration + classification
# ----------------------------
def _calibrate_centroids(face_imgs: dict):
    """Use each face's center sticker as its color centroid in HSV."""
    centroids = {}
    for face, img in face_imgs.items():
        warped = _find_face_warp(img)
        tiles = _slice_face_into_9(warped)
        centroids[face] = _hsv_mean_center_patch(tiles[4])
    return centroids

def _classify_tile(hsv, centroids):
    best_face, best_d = None, 1e9
    for face, c in centroids.items():
        dH = _circular_hue_delta(hsv[0], c[0])
        dS = abs(hsv[1] - c[1])
        dV = abs(hsv[2] - c[2])
        # weight hue most; scale S,V into hue units for balance
        d = 0.6 * dH + 0.25 * (dS / 255 * 180) + 0.15 * (dV / 255 * 180)
        if d < best_d:
            best_d, best_face = d, face
    return best_face

def _build_cube_string(face_imgs, centroids):
    seq = []
    face_sequences = {}  # Track what we detect for each face
    
    for face in FACE_ORDER:
        warped = _find_face_warp(face_imgs[face])
        tiles = _slice_face_into_9(warped)
        face_seq = []
        for t in tiles:
            hsv = _hsv_mean_center_patch(t)
            detected_color = _classify_tile(hsv, centroids)
            face_seq.append(detected_color)
            seq.append(detected_color)
        face_sequences[face] = face_seq
    
    cube = "".join(seq)
    
    # Enhanced error reporting
    color_counts = {}
    for f in FACE_ORDER:
        color_counts[f] = cube.count(f)
        if cube.count(f) != 9:
            # Show detailed breakdown
            error_details = []
            for face_name, face_colors in face_sequences.items():
                count = face_colors.count(f)
                if count > 0:
                    error_details.append(f"{face_name} face: {count} {f} stickers")
            
            raise ValueError(
                f"Count mismatch for {f}: got {cube.count(f)} but need exactly 9.\n"
                f"Breakdown: {', '.join(error_details)}\n"
                f"All color counts: {color_counts}\n"
                f"This usually means lighting issues or similar colors being confused. "
                f"Try retaking photos with better lighting."
            )
    return cube

# ----------------------------
# Solve with orientation sampling
# ----------------------------
def _solve_best_orientation(state):
    """Run Kociemba across several relabelings and keep shortest string of moves."""
    best = kociemba.solve(state)
    best_len = len(best.split())
    for T in _rotations_sample(n=12):
        try:
            cand = kociemba.solve(state.translate(T))
            cand_back = _relabel_moves(cand, T)
            L = len(cand_back.split())
            if L < best_len:
                best, best_len = cand_back, L
        except Exception:
            pass
    return best

# ----------------------------
# Flask endpoints
# ----------------------------
@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/debug-colors")
def debug_colors():
    """
    Debug endpoint to see what colors are detected without solving
    """
    try:
        # 1) Read images from form
        imgs = {}
        for f in FACE_ORDER:
            file = request.files.get(f)
            if not file:
                return (f"Missing face {f}", 400)
            file_bytes = np.frombuffer(file.read(), np.uint8)
            img = cv.imdecode(file_bytes, cv.IMREAD_COLOR)
            if img is None:
                return (f"Failed to decode image for face {f}", 400)
            imgs[f] = img

        # 2) Calibrate & parse cube
        cents = _calibrate_centroids(imgs)
        
        # 3) Get detailed color analysis
        color_analysis = {}
        for face in FACE_ORDER:
            warped = _find_face_warp(imgs[face])
            tiles = _slice_face_into_9(warped)
            face_colors = []
            for i, t in enumerate(tiles):
                hsv = _hsv_mean_center_patch(t)
                detected_color = _classify_tile(hsv, cents)
                face_colors.append({
                    "position": i,
                    "detected_color": detected_color,
                    "hsv": hsv.tolist()
                })
            color_analysis[face] = face_colors
        
        # Count totals
        total_counts = {f: 0 for f in FACE_ORDER}
        for face_data in color_analysis.values():
            for tile in face_data:
                total_counts[tile["detected_color"]] += 1
        
        return jsonify({
            "color_analysis": color_analysis,
            "total_counts": total_counts,
            "centroids": {f: c.tolist() for f, c in cents.items()}
        })

    except Exception as e:
        return (f"Debug error: {e}", 400)

@app.post("/solve")
def solve_endpoint():
    """
    Expects 6 multipart fields named exactly: U, R, F, D, L, B
    Returns: {"moves": ["R", "U", "R'", ...], "count": N}
    """
    try:
        # 1) Read images from form
        imgs = {}
        for f in FACE_ORDER:
            file = request.files.get(f)
            if not file:
                return (f"Missing face {f}", 400)
            file_bytes = np.frombuffer(file.read(), np.uint8)
            img = cv.imdecode(file_bytes, cv.IMREAD_COLOR)
            if img is None:
                return (f"Failed to decode image for face {f}", 400)
            imgs[f] = img

        # 2) Calibrate & parse cube
        cents = _calibrate_centroids(imgs)
        cube = _build_cube_string(imgs, cents)

        # 3) Solve
        solution = _solve_best_orientation(cube)
        moves = solution.split()
        return jsonify({"moves": moves, "count": len(moves)})

    except AssertionError as e:
        return (f"Invalid cube: {e}", 400)
    except ValueError as e:
        return (str(e), 400)
    except Exception as e:
        # For debugging; in production, log more and return generic error
        return (f"Error: {e}", 400)

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    print(f"Rubik solver server running on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
