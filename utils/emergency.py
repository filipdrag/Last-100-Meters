import cv2

def emergency_check(drone):
    """Global ESC emergency handler (from OpenCV window)."""
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        print("[EMERGENCY] ESC pressed → landing!")
        try:
            drone.send_rc_control(0, 0, 0, 0)
            drone.land()
        except:
            pass
        cv2.destroyAllWindows()
        raise SystemExit