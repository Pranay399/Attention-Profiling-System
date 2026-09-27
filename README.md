# Real-Time Student Attention Profiling System

A production-quality web application that analyzes authorized student video during an online class and estimates observable attention states in real time. 

The system uses observable, measurable signals (head pose, gaze on screen, face presence) to provide a probabilistic estimate of attention. It strictly avoids claiming to measure a student's psychological state, intelligence, or personality.

## Architecture

This project is organized into multiple independent modules:

1. **`ai/`**: Independent ML pipeline and training code. Contains models trained on the Mendeley Students Attention Detection Dataset (Logistic Regression, Random Forest, XGBoost, MLP). 
2. **`backend/`**: FastAPI server providing CRUD endpoints, WebSocket streaming for real-time events, and connecting the CV pipeline to the ML inference model. Uses SQLite for the prototype.
3. **`frontend/`**: Vite + React + TypeScript frontend with a rich, glassmorphism-inspired dark theme analytics dashboard and a real-time WebRTC browser screen capture interface.
4. **`meeting/`**: Real-time Computer Vision (CV) pipeline powered by MediaPipe, extracting 3D head pose via solvePnP, pupil positions, and gaze estimations.

## Setup and Running Locally

### 1. Backend and AI Dependencies
The backend requires Python 3.9+ and the dependencies listed in `backend/requirements.txt` and `ai/requirements.txt`.

```bash
pip install -r backend/requirements.txt
```

### 2. Frontend Dependencies
The frontend is built with Node.js and npm.

```bash
cd frontend
npm install
```

### 3. Running the System

You need to run both the backend API and the frontend dev server.

**Terminal 1 (Backend):**
```bash
# From the root directory
python run_backend.py
```
*The backend will start at `http://localhost:8000`*

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```
*The frontend will start at `http://localhost:5173`*

## Usage

1. Open the frontend in your browser.
2. The Dashboard shows mock real-time data across active sessions.
3. Click on the **Live Sessions** or navigate to `/sessions`.
4. Click **Request Screen Capture** and select the Google Meet tab (or any video source).
5. The application will downscale and stream the frames to the FastAPI backend via WebSockets.
6. The backend extracts MediaPipe features, runs inference using the Logistic Regression model, and sends back `attention_alert` and `participant_state` events!

## Key Design Principles

- **No Fake AI**: The system uses real ML models trained on real data.
- **Privacy-First**: Video streams are processed in memory and immediately discarded. Only structured events (attention probabilities) are saved to the database.
- **Robust Event Engine**: Uses Exponentially Weighted Moving Averages (EWMA) to smooth predictions, and employs cooldown mechanisms to prevent alert fatigue.
