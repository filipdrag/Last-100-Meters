# -----------------------------
# Thermal safety helper
# -----------------------------

import time

def thermal_idle_big(drone, seconds: float = 0.25):
    """
    Short motor idle pulse to cool ESC, CPU and WiFi.
    Call this regularly during long vision/LED/voice phases.
    """
    drone.drone.send_rc_control(0, 0, 0, 0)
    time.sleep(seconds)

def thermal_idle_micro(drone, dt=0.02):
    """
    Super short motor idle pulse to cool ESC, CPU and WiFi.
    Call this in realtime-loops.
    """
    drone.drone.send_rc_control(0,0,0,0)
    time.sleep(dt)