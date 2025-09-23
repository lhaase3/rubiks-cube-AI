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
    # Convert both tables to string->string format first
    a_dict = {}
    for k, v in a.items():
        key = chr(k) if isinstance(k, int) else k
        val = chr(v) if isinstance(v, int) else v
        a_dict[key] = val
    
    b_dict = {}
    for k, v in b.items():
        key = chr(k) if isinstance(k, int) else k
        val = chr(v) if isinstance(v, int) else v
        b_dict[key] = val
    
    # Now compose the mappings
    out = {}
    for ch in "URFDLB":
        mid = b_dict.get(ch, ch)
        final = a_dict.get(mid, mid)
        out[ch] = final
    
    # Convert back to ord->ord format for maketrans
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

def _extract_color_features(img_bgr, patch_frac=0.6):
    """Extract multiple color features for more robust classification."""
    try:
        h, w = img_bgr.shape[:2]
        ph, pw = int(h * patch_frac), int(w * patch_frac)
        y0 = (h - ph) // 2
        x0 = (w - pw) // 2
        patch = img_bgr[y0:y0 + ph, x0:x0 + pw]
        
        # Ensure patch is not empty
        if patch.size == 0:
            raise ValueError("Empty patch extracted")
        
        # Multiple color spaces for robustness
        hsv = cv.cvtColor(patch, cv.COLOR_BGR2HSV)
        lab = cv.cvtColor(patch, cv.COLOR_BGR2LAB)
        rgb = cv.cvtColor(patch, cv.COLOR_BGR2RGB)
        
        # Calculate statistics
        hsv_mean = np.mean(hsv.reshape(-1, 3), axis=0)
        lab_mean = np.mean(lab.reshape(-1, 3), axis=0)
        rgb_mean = np.mean(rgb.reshape(-1, 3), axis=0)
        
        # Calculate dominant color using clustering
        pixels = patch.reshape(-1, 3)
        
        # Remove outliers (very dark or very bright pixels)
        brightness = np.mean(pixels, axis=1)
        valid_mask = (brightness > 30) & (brightness < 225)
        if np.sum(valid_mask) > 10:
            pixels = pixels[valid_mask]
        
        # Simple k-means alternative: find most frequent color in quantized space
        quantized = (pixels // 32) * 32  # Quantize to reduce noise
        unique_colors, counts = np.unique(quantized.reshape(-1, 3), axis=0, return_counts=True)
        dominant_bgr = unique_colors[np.argmax(counts)]
        dominant_hsv = cv.cvtColor(dominant_bgr.reshape(1, 1, 3), cv.COLOR_BGR2HSV)[0, 0]
        
        return {
            'hsv_mean': hsv_mean,
            'lab_mean': lab_mean,
            'rgb_mean': rgb_mean,
            'dominant_hsv': dominant_hsv,
            'dominant_bgr': dominant_bgr
        }
    except Exception as e:
        print(f"Error in _extract_color_features: {e}")
        # Return fallback features
        h, w = img_bgr.shape[:2]
        center_pixel = img_bgr[h//2, w//2]
        hsv_center = cv.cvtColor(center_pixel.reshape(1, 1, 3), cv.COLOR_BGR2HSV)[0, 0]
        return {
            'hsv_mean': hsv_center,
            'lab_mean': np.array([50, 0, 0]),  # Neutral LAB
            'rgb_mean': center_pixel,
            'dominant_hsv': hsv_center,
            'dominant_bgr': center_pixel
        }

def _hsv_mean_center_patch(img_bgr, patch_frac=0.4):
    """Legacy function - now uses enhanced feature extraction."""
    features = _extract_color_features(img_bgr, patch_frac)
    return features['hsv_mean']

def _calibrate_centroids_enhanced(face_imgs: dict):
    """Enhanced calibration using multiple color features."""
    centroids = {}
    all_features = {}
    
    for face, img in face_imgs.items():
        warped = _find_face_warp(img)
        tiles = _slice_face_into_9(warped)
        center_tile = tiles[4]  # Center sticker
        
        features = _extract_color_features(center_tile)
        centroids[face] = features['hsv_mean']  # Keep legacy format for now
        all_features[face] = features
    
    # Validate that we have reasonable color separation
    faces = list(centroids.keys())
    min_separation = float('inf')
    
    for i in range(len(faces)):
        for j in range(i + 1, len(faces)):
            f1, f2 = faces[i], faces[j]
            hsv1, hsv2 = centroids[f1], centroids[f2]
            
            # Calculate perceptual distance
            dH = _circular_hue_delta(hsv1[0], hsv2[0])
            dS = abs(hsv1[1] - hsv2[1])
            dV = abs(hsv1[2] - hsv2[2])
            
            # Weighted distance
            distance = 0.6 * dH + 0.25 * (dS / 255 * 180) + 0.15 * (dV / 255 * 180)
            min_separation = min(min_separation, distance)
    
    # If colors are too similar, try using LAB space features
    if min_separation < 15:  # Colors are very similar
        print(f"Warning: Colors appear similar (min separation: {min_separation:.1f}). Using enhanced features.")
        # Could implement LAB-based classification here for better separation
    
    return centroids, all_features

def _classify_tile_enhanced(features, centroids, all_features=None):
    """Enhanced tile classification with multiple features and confidence scoring."""
    hsv = features['hsv_mean']
    lab = features['lab_mean']
    
    candidates = []
    
    for face, centroid_hsv in centroids.items():
        # HSV distance (primary)
        dH = _circular_hue_delta(hsv[0], centroid_hsv[0])
        dS = abs(hsv[1] - centroid_hsv[1])
        dV = abs(hsv[2] - centroid_hsv[2])
        hsv_distance = 0.6 * dH + 0.25 * (dS / 255 * 180) + 0.15 * (dV / 255 * 180)
        
        # LAB distance (secondary, more perceptually uniform)
        lab_distance = 0
        if all_features and face in all_features:
            ref_lab = all_features[face]['lab_mean']
            lab_distance = np.linalg.norm(lab - ref_lab)
        
        # Combined score (lower is better)
        combined_distance = hsv_distance + (lab_distance * 0.1)
        
        candidates.append((face, combined_distance, hsv_distance, lab_distance))
    
    # Sort by combined distance
    candidates.sort(key=lambda x: x[1])
    
    best_face = candidates[0][0]
    best_distance = candidates[0][1]
    second_best_distance = candidates[1][1] if len(candidates) > 1 else float('inf')
    
    # Calculate confidence (higher when there's clear separation)
    confidence = (second_best_distance - best_distance) / (second_best_distance + 1e-6)
    
    return best_face, confidence

def _enhance_image(img_bgr):
    """Preprocess image for better color detection and edge detection."""
    # Convert to LAB for better color representation
    lab = cv.cvtColor(img_bgr, cv.COLOR_BGR2LAB)
    l, a, b = cv.split(lab)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
    clahe = cv.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l_enhanced = clahe.apply(l)
    
    # Merge back and convert to BGR
    lab_enhanced = cv.merge([l_enhanced, a, b])
    enhanced_bgr = cv.cvtColor(lab_enhanced, cv.COLOR_LAB2BGR)
    
    # Apply bilateral filter to reduce noise while preserving edges
    filtered = cv.bilateralFilter(enhanced_bgr, 9, 75, 75)
    
    return filtered

def _find_largest_square_contour(gray):
    """Find the largest square-like contour in the image."""
    # Try multiple Canny thresholds
    thresholds = [(50, 150), (30, 100), (70, 200), (100, 250)]
    best_contour = None
    best_area = 0
    
    for low, high in thresholds:
        edges = cv.Canny(gray, low, high)
        
        # Apply morphological operations to close gaps
        kernel = np.ones((3,3), np.uint8)
        edges = cv.morphologyEx(edges, cv.MORPH_CLOSE, kernel)
        
        contours, _ = cv.findContours(edges, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv.contourArea(contour)
            if area < 1000:  # Skip small contours
                continue
                
            # Approximate to polygon
            peri = cv.arcLength(contour, True)
            approx = cv.approxPolyDP(contour, 0.02 * peri, True)
            
            # Look for quadrilaterals
            if len(approx) == 4:
                # Check if it's roughly square
                pts = approx.reshape(4, 2)
                
                # Calculate side lengths
                sides = []
                for i in range(4):
                    p1 = pts[i]
                    p2 = pts[(i + 1) % 4]
                    side_len = np.linalg.norm(p1 - p2)
                    sides.append(side_len)
                
                # Check if sides are roughly equal (square-like)
                min_side, max_side = min(sides), max(sides)
                aspect_ratio = min_side / max_side if max_side > 0 else 0
                
                if aspect_ratio > 0.7 and area > best_area:  # Reasonably square and larger
                    best_contour = approx
                    best_area = area
    
    return best_contour

def _find_face_warp(img_bgr, out_size=600):
    """Enhanced face detection with better preprocessing and multiple strategies."""
    h, w = img_bgr.shape[:2]
    
    # Strategy 1: Enhanced image processing
    enhanced = _enhance_image(img_bgr)
    gray = cv.cvtColor(enhanced, cv.COLOR_BGR2GRAY)
    blur = cv.GaussianBlur(gray, (5, 5), 0)
    
    # Try to find the best square contour
    best_contour = _find_largest_square_contour(blur)
    
    if best_contour is not None:
        approx = best_contour
    else:
        # Strategy 2: Grid-based detection for when contours fail
        # Look for regular grid patterns (cube faces have 3x3 grids)
        gray_blur = cv.GaussianBlur(gray, (3, 3), 0)
        
        # Use adaptive threshold to find grid lines
        adaptive = cv.adaptiveThreshold(gray_blur, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv.THRESH_BINARY, 11, 2)
        
        # Look for horizontal and vertical lines
        horizontal_kernel = cv.getStructuringElement(cv.MORPH_RECT, (25, 1))
        vertical_kernel = cv.getStructuringElement(cv.MORPH_RECT, (1, 25))
        
        horizontal_lines = cv.morphologyEx(adaptive, cv.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv.morphologyEx(adaptive, cv.MORPH_OPEN, vertical_kernel)
        
        # Combine lines
        grid = cv.bitwise_or(horizontal_lines, vertical_lines)
        
        # Find contours in the grid
        contours, _ = cv.findContours(grid, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find the largest rectangular contour
            largest_contour = max(contours, key=cv.contourArea)
            peri = cv.arcLength(largest_contour, True)
            approx = cv.approxPolyDP(largest_contour, 0.02 * peri, True)
            
            if len(approx) != 4:
                # Fallback: use bounding rectangle
                x, y, w_rect, h_rect = cv.boundingRect(largest_contour)
                approx = np.array([[[x, y]], [[x + w_rect, y]], 
                                 [[x + w_rect, y + h_rect]], [[x, y + h_rect]]], dtype=np.int32)
        else:
            # Strategy 3: Center crop (most conservative fallback)
            margin = min(w, h) // 6
            approx = np.array([[[margin, margin]], [[w - margin, margin]], 
                             [[w - margin, h - margin]], [[margin, h - margin]]], dtype=np.int32)

    # Order points consistently: top-left, top-right, bottom-right, bottom-left
    pts = approx.reshape(4, 2).astype(np.float32)
    
    # Find corners more robustly
    center = np.mean(pts, axis=0)
    
    # Sort by angle from center
    def angle_from_center(point):
        return np.arctan2(point[1] - center[1], point[0] - center[0])
    
    sorted_pts = sorted(pts, key=angle_from_center)
    
    # Identify corners based on their position relative to center
    tl = min(sorted_pts, key=lambda p: p[0] + p[1])  # Smallest x + y
    br = max(sorted_pts, key=lambda p: p[0] + p[1])  # Largest x + y
    tr = min(sorted_pts, key=lambda p: p[1] - p[0])  # Smallest y - x
    bl = max(sorted_pts, key=lambda p: p[1] - p[0])  # Largest y - x
    
    dst = np.array([[0, 0], [out_size, 0], [out_size, out_size], [0, out_size]], dtype=np.float32)
    src = np.array([tl, tr, br, bl], dtype=np.float32)
    
    M = cv.getPerspectiveTransform(src, dst)
    warped = cv.warpPerspective(enhanced, M, (out_size, out_size))
    
    return warped

def _slice_face_into_9(warped):
    H, W = warped.shape[:2]
    h, w = H // 3, W // 3
    tiles = []
    for r in range(3):
        for c in range(3):
            y1, y2 = r * h, (r + 1) * h
            x1, x2 = c * w, (c + 1) * w
            tile = warped[y1:y2, x1:x2]
            tiles.append(tile)
    return tiles

# ----------------------------
# Color calibration + classification
# ----------------------------
def _calibrate_centroids(face_imgs: dict):
    """Use each face's center sticker as its color centroid in HSV."""
    centroids, all_features = _calibrate_centroids_enhanced(face_imgs)
    return centroids

def _classify_tile(hsv, centroids):
    """Legacy classification function - converts HSV to features format."""
    features = {'hsv_mean': hsv, 'lab_mean': np.array([0, 0, 0])}
    best_face, confidence = _classify_tile_enhanced(features, centroids)
    return best_face

def _build_cube_string(face_imgs, centroids):
    """Build cube string with enhanced feature extraction and validation."""
    print("Starting cube string building...")
    
    # First pass: get enhanced centroids
    print("Getting enhanced centroids...")
    centroids_enhanced, all_features = _calibrate_centroids_enhanced(face_imgs)
    print(f"Enhanced centroids obtained for faces: {list(centroids_enhanced.keys())}")
    
    seq = []
    face_sequences = {}
    confidence_scores = {}
    
    for face in FACE_ORDER:
        print(f"Processing face {face}...")
        try:
            warped = _find_face_warp(face_imgs[face])
            print(f"Face {face} warped to shape: {warped.shape}")
            
            tiles = _slice_face_into_9(warped)
            print(f"Face {face} sliced into {len(tiles)} tiles")
            
            face_seq = []
            face_confidences = []
            
            for i, tile in enumerate(tiles):
                try:
                    print(f"Processing tile {i} of face {face}, tile shape: {tile.shape}")
                    features = _extract_color_features(tile)
                    detected_color, confidence = _classify_tile_enhanced(features, centroids_enhanced, all_features)
                    face_seq.append(detected_color)
                    face_confidences.append(confidence)
                    seq.append(detected_color)
                    print(f"Tile {i}: {detected_color} (confidence: {confidence:.3f})")
                except Exception as e:
                    print(f"Error processing tile {i} of face {face}: {e}")
                    # Use fallback classification
                    hsv = _hsv_mean_center_patch(tile)
                    detected_color = _classify_tile(hsv, centroids_enhanced)
                    face_seq.append(detected_color)
                    face_confidences.append(0.1)  # Low confidence for fallback
                    seq.append(detected_color)
                    print(f"Fallback tile {i}: {detected_color}")
            
            face_sequences[face] = face_seq
            confidence_scores[face] = face_confidences
            
            # Validate center sticker matches expected face color
            center_color = face_seq[4]  # Center tile should match face name
            center_confidence = face_confidences[4]
            
            if center_color != face:
                print(f"Warning: {face} face center sticker detected as {center_color} "
                      f"(confidence: {center_confidence:.2f}). This might indicate incorrect face labeling.")
                      
        except Exception as e:
            print(f"ERROR processing face {face}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    cube = "".join(seq)
    print(f"Generated cube string: {cube}")
    
    # Calculate average confidence per face
    avg_confidences = {}
    for face, confidences in confidence_scores.items():
        avg_confidences[face] = np.mean(confidences)
    
    # Enhanced error reporting with confidence scores
    color_counts = {}
    low_confidence_faces = []
    
    for f in FACE_ORDER:
        color_counts[f] = cube.count(f)
        
        if avg_confidences[f] < 0.3:  # Low confidence threshold
            low_confidence_faces.append(f"{f} (avg confidence: {avg_confidences[f]:.2f})")
        
        if cube.count(f) != 9:
            # Show detailed breakdown
            error_details = []
            for face_name, face_colors in face_sequences.items():
                count = face_colors.count(f)
                if count > 0:
                    error_details.append(f"{face_name} face: {count} {f} stickers")
            
            confidence_info = ""
            if low_confidence_faces:
                confidence_info = f"\nLow confidence detections: {', '.join(low_confidence_faces)}"
            
            error_msg = (
                f"Count mismatch for {f}: got {cube.count(f)} but need exactly 9.\n"
                f"Breakdown: {', '.join(error_details)}\n"
                f"All color counts: {color_counts}{confidence_info}\n"
                f"This usually means lighting issues or similar colors being confused. "
                f"Try retaking photos with better lighting, ensuring the cube face fills most of the frame."
            )
            print(f"CUBE VALIDATION ERROR: {error_msg}")
            raise ValueError(error_msg)
    
    print("Cube string validation passed!")
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
    Enhanced debug endpoint with detailed color analysis and confidence scores
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

        # 2) Enhanced calibration & analysis
        centroids, all_features = _calibrate_centroids_enhanced(imgs)
        
        # 3) Get detailed color analysis with confidence scores
        color_analysis = {}
        face_statistics = {}
        
        for face in FACE_ORDER:
            warped = _find_face_warp(imgs[face])
            tiles = _slice_face_into_9(warped)
            face_colors = []
            confidences = []
            
            for i, tile in enumerate(tiles):
                features = _extract_color_features(tile)
                detected_color, confidence = _classify_tile_enhanced(features, centroids, all_features)
                
                face_colors.append({
                    "position": i,
                    "detected_color": detected_color,
                    "confidence": round(confidence, 3),
                    "hsv_mean": features['hsv_mean'].tolist(),
                    "lab_mean": features['lab_mean'].tolist(),
                    "dominant_hsv": features['dominant_hsv'].tolist()
                })
                confidences.append(confidence)
            
            color_analysis[face] = face_colors
            
            # Calculate face statistics
            unique_colors = list(set([tile["detected_color"] for tile in face_colors]))
            center_color = face_colors[4]["detected_color"]
            center_confidence = face_colors[4]["confidence"]
            avg_confidence = np.mean(confidences)
            
            face_statistics[face] = {
                "unique_colors": unique_colors,
                "center_color": center_color,
                "center_matches_face": center_color == face,
                "center_confidence": round(center_confidence, 3),
                "average_confidence": round(avg_confidence, 3),
                "total_tiles": len(face_colors)
            }
        
        # Count totals
        all_detections = []
        for face_data in color_analysis.values():
            for tile in face_data:
                all_detections.append(tile["detected_color"])
        
        total_counts = {f: all_detections.count(f) for f in FACE_ORDER}
        
        # Calculate overall statistics
        all_confidences = []
        for face_data in color_analysis.values():
            for tile in face_data:
                all_confidences.append(tile["confidence"])
        
        overall_stats = {
            "total_tiles_analyzed": len(all_detections),
            "average_confidence": round(np.mean(all_confidences), 3),
            "min_confidence": round(np.min(all_confidences), 3),
            "max_confidence": round(np.max(all_confidences), 3),
            "colors_with_correct_count": sum(1 for count in total_counts.values() if count == 9),
            "faces_with_correct_center": sum(1 for stats in face_statistics.values() if stats["center_matches_face"])
        }
        
        return jsonify({
            "color_analysis": color_analysis,
            "face_statistics": face_statistics,
            "total_counts": total_counts,
            "overall_statistics": overall_stats,
            "centroids": {f: c.tolist() for f, c in centroids.items()},
            "status": "success" if overall_stats["colors_with_correct_count"] == 6 else "needs_improvement",
            "recommendations": _generate_recommendations(face_statistics, total_counts, overall_stats)
        })

    except Exception as e:
        return (f"Debug error: {e}", 400)

def _generate_recommendations(face_statistics, total_counts, overall_stats):
    """Generate helpful recommendations based on analysis."""
    recommendations = []
    
    # Check for low confidence
    if overall_stats["average_confidence"] < 0.5:
        recommendations.append("Overall confidence is low. Try better lighting or cleaner cube faces.")
    
    # Check for incorrect center colors
    wrong_centers = [face for face, stats in face_statistics.items() if not stats["center_matches_face"]]
    if wrong_centers:
        recommendations.append(f"Center stickers incorrectly detected for faces: {', '.join(wrong_centers)}. Check face labeling.")
    
    # Check for count mismatches
    wrong_counts = [f"{face}: {count}" for face, count in total_counts.items() if count != 9]
    if wrong_counts:
        recommendations.append(f"Incorrect color counts detected: {', '.join(wrong_counts)}. Retake photos with better lighting.")
    
    # Check for very similar colors
    if overall_stats["min_confidence"] < 0.2:
        recommendations.append("Some colors are very similar. Ensure good lighting contrast between cube stickers.")
    
    if not recommendations:
        recommendations.append("Color detection looks good! Ready to solve.")
    
    return recommendations

@app.post("/solve")
def solve_endpoint():
    """
    Expects 6 multipart fields named exactly: U, R, F, D, L, B
    Returns: {"moves": ["R", "U", "R'", ...], "count": N}
    """
    try:
        print("=== SOLVE REQUEST RECEIVED ===")
        print(f"Files in request: {list(request.files.keys())}")
        
        # 1) Read images from form
        imgs = {}
        for f in FACE_ORDER:
            file = request.files.get(f)
            if not file:
                error_msg = f"Missing face {f}"
                print(f"ERROR: {error_msg}")
                return (error_msg, 400)
            
            print(f"Processing face {f}: {file.filename}, size: {file.content_length}")
            file_bytes = np.frombuffer(file.read(), np.uint8)
            img = cv.imdecode(file_bytes, cv.IMREAD_COLOR)
            if img is None:
                error_msg = f"Failed to decode image for face {f}"
                print(f"ERROR: {error_msg}")
                return (error_msg, 400)
            print(f"Successfully decoded face {f}: shape {img.shape}")
            imgs[f] = img

        print("All images loaded successfully")
        
        # 2) Calibrate & parse cube
        print("Starting calibration...")
        cents = _calibrate_centroids(imgs)
        print(f"Calibration complete: {list(cents.keys())}")
        
        print("Building cube string...")
        cube = _build_cube_string(imgs, cents)
        print(f"Cube string built: {cube[:20]}... (length: {len(cube)})")

        # 3) Solve
        print("Solving cube...")
        solution = _solve_best_orientation(cube)
        moves = solution.split()
        print(f"Solution found: {len(moves)} moves")
        return jsonify({"moves": moves, "count": len(moves)})

    except AssertionError as e:
        error_msg = f"Invalid cube: {e}"
        print(f"ASSERTION ERROR: {error_msg}")
        return (error_msg, 400)
    except ValueError as e:
        error_msg = str(e)
        print(f"VALUE ERROR: {error_msg}")
        return (error_msg, 400)
    except Exception as e:
        import traceback
        error_msg = f"Unexpected error: {e}"
        print(f"EXCEPTION: {error_msg}")
        print("TRACEBACK:")
        traceback.print_exc()
        return (error_msg, 400)

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    print(f"Rubik solver server running on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
