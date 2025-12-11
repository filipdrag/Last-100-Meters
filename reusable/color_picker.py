import cv2
from djitellopy import Tello

clicked_pos = None


def on_mouse(event, x, y, flags, param):
    global clicked_pos
    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_pos = (x, y)


def main():
    drone = Tello()
    drone.connect()
    print("Battery:", drone.get_battery(), "%")

    drone.streamon()
    frame_reader = drone.get_frame_read()

    cv2.namedWindow("Tello picker")
    cv2.setMouseCallback("Tello picker", on_mouse)

    try:
        while True:
            frame = frame_reader.frame
            if frame is None:
                continue

            # flip if you need it
            frame = cv2.flip(frame, 0)

            display = frame.copy()
            if clicked_pos is not None:
                x, y = clicked_pos
                cv2.circle(display, (x, y), 5, (0, 0, 255), -1)

                b, g, r = frame[y, x]
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                h, s, v = hsv[y, x]

                print(
                    f"Clicked at ({x},{y})  BGR=({b},{g},{r})  HSV=({h},{s},{v})")

            cv2.imshow("Tello picker", display)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:   # ESC
                break

    finally:
        cv2.destroyAllWindows()
        drone.streamoff()
        drone.end()


if __name__ == "__main__":
    main()
