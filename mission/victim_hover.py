import time
from utils.thermal_safety_helper import thermal_idle_big, thermal_idle_micro
import random


def victim_hover(drone):
    # stop all motion commands
    drone.drone.send_rc_control(0, 0, 0, 0)
    time.sleep(0.2)   # IMPORTANT: exit RC timing window

    #Show +
    drone.show_pattern("CROSS")
    time.sleep(2)

    

def ask_yes_no(drone, voice, question, wait_timeout_s: float = 25.0):
    #cool down drone
    thermal_idle_big(drone)
    
    # Show question mark while speaking
    drone.show_pattern("QUESTION_MARK")
    voice.say(question)

    # Show dots while waiting for answer
    drone.show_pattern("DOTS")
    time.sleep(2.0)

    # Show "YES"/"NO" as moving text after recognition
    text = random.choice(["YES", "NO"])
    drone.show_moving_text_once(text, color="g", speed=0.08)
    
    drone.clear_led("g")
    
    #cool down drone
    thermal_idle_big(drone)

def victim_communication(drone, voice):
    # Optional: approach sequence (edit to your needs)
    voice.say(
        "We are from the ambulance service. For the following questions, answer by showing a thumbs up for yes, "
        "or thumbs down for no."
    )

    ask_yes_no(drone, voice,"Can you hear me?")

    ask_yes_no(
        drone, voice, "Is thid the medical emergency that called the ambulance?")

    voice.say("Help is on its way.")

    ask_yes_no(
        drone, voice, "Did the medical situation get worse since the call?")

    ask_yes_no(
        drone, voice, "Are any medical actions currently being done?")

    ask_yes_no(
        drone, voice, "Is the patient in a safe and stable position?")

    drone.show_pattern("CROSS")
    voice.say("I am now heading back to guide the ambulance to you. Please stay here.")


