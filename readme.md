# Last 100 Meters – Tello Drone Guidance

This project controls a **Tello drone** to locate patients and guide rescue teams. The drone can **fly a predefined path backwards**, **display LED matrix patterns**, and perform simple **communication prompts**.

## Features

- Fly a given path backwards so the LED matrix faces backward
- Compress multiple steps in one direction into a single movement
- Display LED patterns **before every movement or rotation**
- Communicate with "victims" via visual cues (Yes/No)
- Supports both **Conda** and **virtual Python environments**

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/last-100-meters.git
cd last-100-meters
```

2. **Create a Python environment (recommended: Conda or venv):**

Conda:
```bash
conda create -n tello_env python=3.11
conda activate tello_env
pip install -r requirements.txt
```

Virtual Environment:
```bash
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

## Usage

1. Connect your Tello drone to your PC or laptop.
2. Run the main script:

```bash
python main.py
```


3. The drone will automatically handle victim finding, route calculation, navigation, and LED matrix guidance.

## Project Structure

- main.py – Entry point for the mission
- mission/ – Mission controller and flight logic
- drone/ – Low-level Tello commands, LED matrix, and worker thread
- visuals/ - Detection of Aruco marker and frame processing
- utils/ – Helper functions (e.g., Converters, emergency_check)
- requirements.txt – Python dependencies
- .gitignore – Ignored files, virtual environments, logs

## LED Matrix Patterns

- CROSS – Victim found
- UP – Moving backward
- TURN_LEFT / TURN_RIGHT – Before rotation
- PARKING – Parking spot reached
- X_SHAPE – Arrived at target
- HOMING – Returning to start

## Notes

- Emergency stop: Press ESC during the mission to immediately stop the drone
- Dependencies: All required libraries are listed in requirements.txt
- Python version: 3.10 recommended
- Battery: Ensure the drone is sufficiently charged before starting
