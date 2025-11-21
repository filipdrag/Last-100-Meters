# Test imports of all required libraries

# Importing the libraries
import pyaudio  # For audio input/output
import speech_recognition as sr  # For speech recognition
import pygame  # For visual interaction (game development)
from PyQt5.QtWidgets import QApplication, QWidget  # For GUI creation
import cv2  # For image processing
import numpy as np  # For numerical computations
import matplotlib.pyplot as plt  # For data visualization
import mediapipe as mp  # For hand and gesture detection
import cvzone  # For simplified OpenCV usage
import keyboard  # For keyboard input detection
from djitellopy import Tello  # For controlling Tello drone


 # Commented out Test djitellopy (Tello drone)
try:
     tello = Tello()
     tello.connect()
     print(f"Battery: {tello.get_battery()}%")
except Exception as e:
     print(f"Error with Tello: {e}")

# Test PyAudio (For audio input/output)
try:
    pyaudio.PyAudio()  # Just initialize PyAudio
    print("PyAudio is successfully installed.")
except Exception as e:
    print(f"Error with PyAudio: {e}")

# Test SpeechRecognition (For voice recognition)
try:
    recognizer = sr.Recognizer()  # Initialize recognizer
    print("SpeechRecognition is successfully installed.")
except Exception as e:
    print(f"Error with SpeechRecognition: {e}")

# Test Pygame (For visual interaction)
try:
    pygame.init()  # Initialize Pygame
    print("Pygame is successfully installed.")
except Exception as e:
    print(f"Error with Pygame: {e}")

# Test PyQt5 (For graphical user interface)
try:
    app = QApplication([])  # Initialize the Qt application
    window = QWidget()  # Create a window
    window.setWindowTitle("Test PyQt5")  # Set the window title
    window.show()  # Show the window
    print("PyQt5 is successfully installed.")
except Exception as e:
    print(f"Error with PyQt5: {e}")

# Test OpenCV (cv2) for image processing
try:
    img = np.zeros((100, 100, 3), dtype=np.uint8)  # Create a blank image
    cv2.imshow("Test OpenCV", img)  # Display the image
    cv2.waitKey(0)  # Wait for a key event
    cv2.destroyAllWindows()
    print("OpenCV is successfully installed.")
except Exception as e:
    print(f"Error with OpenCV: {e}")

# Test NumPy for numerical computations
try:
    arr = np.array([1, 2, 3, 4])  # Create a simple NumPy array
    print(f"NumPy is successfully installed: {arr}")
except Exception as e:
    print(f"Error with NumPy: {e}")

# Test Matplotlib for data visualization
try:
    plt.plot([1, 2, 3, 4], [10, 20, 25, 30])  # Simple line plot
    plt.show()  # Show the plot
    print("Matplotlib is successfully installed.")
except Exception as e:
    print(f"Error with Matplotlib: {e}")

# Test MediaPipe for gesture detection
try:
    mp_hands = mp.solutions.hands  # Initialize MediaPipe Hand model
    hands = mp_hands.Hands()
    print("MediaPipe is successfully installed.")
except Exception as e:
    print(f"Error with MediaPipe: {e}")

# Test cvzone (Simplified OpenCV)
try:
    print("cvzone is successfully installed.")
except Exception as e:
    print(f"Error with cvzone: {e}")

# Test Keyboard library (For keyboard input detection)
try:
    if keyboard.is_pressed('a'):  # Check if the 'a' key is pressed
        print("The 'a' key is pressed.")
    print("Keyboard is successfully installed.")
except Exception as e:
    print(f"Error with Keyboard: {e}")
