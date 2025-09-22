# pip install opencv-python numpy kociemba
import cv2 as cv
import numpy as np
import kociemba
import glob
import math
from itertools import product

FACE_ORDER = ["U","R","F","D","L","B"]  # expected filenames like U.jpg etc.
ROT_X = str.maketrans({"U":"B","B":"D","D":"F","F":"U","R":"R","L":"L"})
ROT_Y = str.maketrans({"F":"R","R":"B","B":"L","L":"F","U":"U","D":"D"})
ROT_Z = str.maketrans({"U":"R","R":"D","D":"L","L":"U","F":"F","B":"B"})

def apply_relabel(state, table):
    return state.translate(table)

def capture_faces_from_webcam():
    order = ["U","R","F","D","L","B"]
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("No webcam found")
    print("Align one face in view. Press SPACE to capture, ESC to quit.")
    idx = 0
    while idx < len(order):
        ok, frame = cap.read()
        if not ok: continue
        # simple overlay grid
        h, w = frame.shape[:2]
        step = min(h, w)//3
        for i in range(1,3):
            cv.line(frame, (0, i*step), (w, i*step), (0,255,0), 1)
            cv.line(frame, (i*step, 0), (i*step, h), (0,255,0), 1)
        cv.putText(frame, f"Capture {order[idx]}", (10,30), cv.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv.imshow("Rubik Face Capture", frame)
        key = cv.waitKey(10) & 0xFF
        if key == 27: break           # ESC
        if key == 32:                 # SPACE
            fname = f"{order[idx]}.jpg"
            cv.imwrite(fname, frame)
            print("Saved", fname)
            idx += 1
    cap.release()
    cv.destroyAllWindows()

# call this once before running calibrate/solve:
# capture_faces_from_webcam()

def compose_tables(a, b):
    # compose two translation tables (dict[str->str]) into a new one
    # we’ll represent as dict to compose, then convert to str.maketrans if needed
    ad = {chr(k): chr(v) for k, v in a.items()} if isinstance(a, dict) else {k:v for k,v in a.items()}
    bd = {chr(k): chr(v) for k, v in b.items()} if isinstance(b, dict) else {k:v for k,v in b.items()}
    out = {}
    for ch in "URFDLB":
        mid = bd.get(ch, ch)
        out[ch] = ad.get(mid, mid)
    return {ord(k): ord(v) for k, v in out.items()}  # back to maketrans form

def rotations_sample():
    # Build ~12 orientations by sampling exponents of X,Y,Z
    base = {ord(c): ord(c) for c in "URFDLB"}  # identity
    R = []
    # sample small ranges; (x,y,z) ∈ {0,1,2,3}^3 but with pruning for duplicates
    seen = set()
    for x,y,z in product(range(4), range(3), range(4)):  # 48 combos -> we dedupe
        t = base
        for _ in range(x): t = compose_tables(ROT_X, t)
        for _ in range(y): t = compose_tables(ROT_Y, t)
        for _ in range(z): t = compose_tables(ROT_Z, t)
        key = tuple((k, t[k]) for k in sorted(t.keys()))
        if key not in seen:
            seen.add(key)
            R.append(t)
        if len(R) >= 12:  # good sample; often enough to shave a few moves
            break
    return R

def invert_table(t):
    inv = {}
    for k,v in t.items():
        inv[v] = k
    return inv

def relabel_moves(moves_str, inverse_table):
    # Translate face letters back (keep suffixes like '2 or ')
    back = []
    inv = invert_table(inverse_table)
    for tok in moves_str.split():
        face, suffix = tok[0], tok[1:]
        back_face = chr(inv.get(ord(face), ord(face)))
        back.append(back_face + suffix)
    return " ".join(back)

def solve_best_orientation(state):
    # Single fast attempt first
    import kociemba
    best = kociemba.solve(state)
    best_len = len(best.split())
    best_str = best

    # Try sampled orientations
    for T in rotations_sample():
        s_rel = apply_relabel(state, T)
        try:
            cand = kociemba.solve(s_rel)
            # Map moves back to original labeling
            cand_back = relabel_moves(cand, T)
            L = len(cand_back.split())
            if L < best_len:
                best_len = L
                best_str = cand_back
        except Exception:
            pass
    return best_str

# --- Pretty printing / export ---
MOVE_LONG_NAMES = {
    "U":"Turn the Up face clockwise",
    "D":"Turn the Down face clockwise",
    "L":"Turn the Left face clockwise",
    "R":"Turn the Right face clockwise",
    "F":"Turn the Front face clockwise",
    "B":"Turn the Back face clockwise",
}
def describe_move(token):
    face = token[0]
    suf = token[1:]  # "", "'", "2"
    base = MOVE_LONG_NAMES.get(face, face)
    if suf == "":
        return base
    if suf == "'":
        return base.replace("clockwise", "counter-clockwise")
    if suf == "2":
        return base.replace("clockwise", "180°")
    return token

def show_steps(moves):
    tokens = moves.split()
    print(f"\nShortest found: {len(tokens)} moves\n")
    for i, t in enumerate(tokens, 1):
        print(f"{i:2d}. {t: <3}  – {describe_move(t)}")

def export_json(moves, path="solution.json"):
    import json
    data = {"moves": moves.split()}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {path} with {len(data['moves'])} moves.")

def circular_hue_delta(h1, h2):
    d = abs(h1 - h2)
    return min(d, 180 - d)  # OpenCV hue in [0..180]

def hsv_mean_center_patch(img_bgr, patch_frac=0.4):
    h,w = img_bgr.shape[:2]
    ph, pw = int(h*patch_frac), int(w*patch_frac)
    y0 = (h - ph)//2; x0 = (w - pw)//2
    patch = img_bgr[y0:y0+ph, x0:x0+pw]
    hsv = cv.cvtColor(patch, cv.COLOR_BGR2HSV)
    return np.mean(hsv.reshape(-1,3), axis=0)  # [H,S,V]

def find_face_warp(img_bgr, out_size=600):
    gray = cv.cvtColor(img_bgr, cv.COLOR_BGR2GRAY)
    blur = cv.GaussianBlur(gray, (5,5), 0)
    edges = cv.Canny(blur, 50, 150)
    cnts,_ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    if not cnts: raise ValueError("No contours")
    c = max(cnts, key=cv.contourArea)
    peri = cv.arcLength(c, True)
    approx = cv.approxPolyDP(c, 0.02*peri, True)
    if len(approx) != 4:
        # fallback: assume full frame
        h,w = img_bgr.shape[:2]
        approx = np.array([[[0,0]], [[w,0]], [[w,h]], [[0,h]]], dtype=np.int32)
    pts = approx.reshape(4,2).astype(np.float32)

    # order points: tl, tr, br, bl
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]; br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]; bl = pts[np.argmax(diff)]
    dst = np.array([[0,0],[out_size,0],[out_size,out_size],[0,out_size]], dtype=np.float32)
    M = cv.getPerspectiveTransform(np.array([tl,tr,br,bl],dtype=np.float32), dst)
    warped = cv.warpPerspective(img_bgr, M, (out_size,out_size))
    return warped

def slice_face_into_9(warped):
    H, W = warped.shape[:2]
    cellH, cellW = H//3, W//3
    tiles = []
    for r in range(3):
        for c in range(3):
            tiles.append(warped[r*cellH:(r+1)*cellH, c*cellW:(c+1)*cellW])
    return tiles  # 9 BGR tiles

def calibrate_centroids():
    """Return dict: face_letter -> HSV centroid (from center tile)."""
    centroids = {}
    for face in FACE_ORDER:
        img = cv.imread(f"{face}.jpg")
        if img is None: raise FileNotFoundError(face)
        warped = find_face_warp(img)
        tiles = slice_face_into_9(warped)
        center_tile = tiles[4]
        centroids[face] = hsv_mean_center_patch(center_tile)
    return centroids  # np.array([H,S,V])

def classify_tile(hsv, centroids):
    best_face, best_d = None, 1e9
    for face, c in centroids.items():
        dH = circular_hue_delta(hsv[0], c[0])
        dS = abs(hsv[1]-c[1])
        dV = abs(hsv[2]-c[2])
        d = 0.6*dH + 0.25*dS/255*180 + 0.15*dV/255*180  # scale S,V to hue-ish range
        if d < best_d:
            best_d, best_face = d, face
    return best_face

def build_cube_string(centroids):
    """Return 54-char string in URFDLB order, each 9 stickers row-major."""
    result = []
    for face in FACE_ORDER:
        img = cv.imread(f"{face}.jpg")
        warped = find_face_warp(img)
        tiles = slice_face_into_9(warped)
        for t in tiles:
            hsv = hsv_mean_center_patch(t)
            # classify relative to calibrated *face letters*
            face_letter = classify_tile(hsv, centroids)
            result.append(face_letter)
    cube_str = "".join(result)
    # Quick sanity: 9 of each letter
    for f in FACE_ORDER:
        assert cube_str.count(f) == 9, f"Count mismatch for {f}"
    return cube_str

if __name__ == "__main__":
    # One-time: capture six face images with webcam
    capture_faces_from_webcam()

    # After you’ve already captured and saved U.jpg..B.jpg, you can comment
    # the line above out and just reuse the saved images.

    centroids = calibrate_centroids()
    cube = build_cube_string(centroids)
    print("State:", cube)

    solution = solve_best_orientation(cube)
    print("Solution:", solution)
    show_steps(solution)
    export_json(solution)


