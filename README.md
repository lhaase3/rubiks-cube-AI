# Rubik's Cube AI Solver with 3D Animation

An intelligent Rubik's Cube solver that uses computer vision to analyze cube states and provides animated 3D solutions.

## ✨ Features

### 🔍 Computer Vision Input
- **Photo Upload**: Upload images of each cube face (U, R, F, D, L, B)
- **Live Camera Capture**: Use your webcam to capture cube faces in real-time
- **3×3 Grid Overlay**: Visual guide for proper face alignment during capture

### 🤖 AI-Powered Solving
- **Advanced Computer Vision**: Analyzes cube colors using HSV color space
- **Kociemba Algorithm**: Optimal solving using Two-Phase algorithm
- **Multiple Orientations**: Tests different cube orientations for shortest solutions
- **Error Handling**: Validates cube configurations and provides helpful feedback

### 🎬 3D Animation Viewer
- **Interactive 3D Cube**: Real-time rendered Rubik's cube with proper colors
- **Step-by-Step Animation**: Watch each move animate smoothly in 3D
- **Animation Controls**: 
  - Play all moves automatically
  - Step through moves individually
  - Reset to solved state
  - Pause/resume functionality
- **Move Descriptions**: Human-readable descriptions for each rotation
- **Progress Tracking**: Visual progress indicator and move counter

### 🎨 Modern UI/UX
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Theme**: Sleek dark interface with accent colors
- **Real-time Feedback**: Live status updates and error messages
- **Two-Column Layout**: Input controls alongside 3D visualization

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+ (for the backend solver)
- Webcam (optional, for live capture)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/lhaase3/rubiks-cube-AI.git
   cd rubiks-cube-AI
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Install Python dependencies**
   ```bash
   pip install flask flask-cors opencv-python numpy kociemba
   ```

4. **Set up environment variables**
   ```bash
   # Create .env.local in the root directory
   NEXT_PUBLIC_SOLVER_URL=http://localhost:5001/solve
   ```

### Running the Application

1. **Start the Python backend**
   ```bash
   python server.py
   ```

2. **Start the Next.js frontend**
   ```bash
   npm run dev
   ```

3. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 📱 How to Use

### Step 1: Capture Cube Faces
1. Upload photos or use the camera to capture all 6 faces
2. Ensure good lighting and clear visibility of all 9 stickers per face
3. Follow the standard cube notation: U (Up/White), R (Right/Red), F (Front/Green), D (Down/Yellow), L (Left/Orange), B (Back/Blue)

### Step 2: Solve the Cube
1. Once all faces are captured, click "Solve Cube"
2. The AI will analyze the cube state and find the optimal solution
3. View the solution summary with move count

### Step 3: Watch the 3D Animation
1. The 3D viewer shows your cube's solution
2. Use "Play All" to see the complete solution animated
3. Click individual moves to step through manually
4. Use mouse controls to rotate and zoom the 3D view
5. "Reset" returns the cube to its initial state

## 🔧 Technical Stack

### Frontend
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Three.js**: 3D graphics and animation
- **React Three Fiber**: React renderer for Three.js
- **React Three Drei**: Utility library for 3D components

### Backend
- **Flask**: Python web framework
- **OpenCV**: Computer vision and image processing
- **NumPy**: Numerical computations
- **Kociemba**: Rubik's cube solving algorithm
- **Flask-CORS**: Cross-origin resource sharing

### Computer Vision Pipeline
1. **Image Preprocessing**: Gaussian blur, edge detection
2. **Face Detection**: Contour detection and perspective correction
3. **Color Calibration**: HSV-based color classification using center stickers
4. **Grid Extraction**: 3×3 sticker grid analysis
5. **State Validation**: Ensures valid cube configuration

## 🎮 3D Controls

- **Mouse Drag**: Rotate the cube view
- **Mouse Wheel**: Zoom in/out
- **Right Click + Drag**: Pan the view
- **Double Click**: Reset camera position

## 🎨 Cube Notation

Standard WCA notation is used:
- **U**: Up face (White) - clockwise 90°
- **U'**: Up face - counter-clockwise 90°
- **U2**: Up face - 180°
- **R, L, F, B, D**: Right, Left, Front, Back, Down faces
- **Modifiers**: `'` (prime) = counter-clockwise, `2` = double turn

## 🚨 Troubleshooting

### Common Issues
- **Camera not working**: Check browser permissions for camera access
- **Poor color detection**: Ensure good lighting and avoid shadows
- **Invalid cube error**: Verify all faces are captured correctly
- **3D viewer not loading**: Ensure WebGL is supported in your browser

### Performance Tips
- Use good lighting for better color detection
- Avoid reflective surfaces that cause glare
- Ensure cube faces are clearly visible and in focus
- Use the grid overlay as a guide for proper alignment

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 🔮 Future Enhancements

- Support for larger cubes (4×4, 5×5)
- Voice commands for move input
- Cube scramble generator
- Solution sharing and saving
- Mobile app version
- AR overlay for real cube solving
- Multiplayer solving competitions