from machine import Pin, PWM
from time import sleep
from math import floor

# Arm with forward-back-neutral OR back-forward-neu, where the neu must be at least 500ms
# and for/rev are 2 cycles
# Max duty cycle is 65535


def arm_esc(pin):
    pin.duty_u16(13107)
    sleep(0.02)
    pin.duty_u16(6553)
    sleep(0.02)
    pin.duty_u16(9830)
    sleep(0.5)

# Convert % power to duty cycle
# Bounded to [20%, 80%] power
def convert_speed(percent):
    if percent < 0.2:
        percent = 0.2
    elif precent > 0.8:
        percent = 0.8
    duty = floor((1.5 + (percent * 0.5))/10 * 65535)
    return duty

# Convert angle (degrees) to the nano seconds
# angle: [-45, 45]
def convert_angle(angle):
    if angle == 0: # straight
        ms = 1.5
    else:
        if angle < -45:
            angle = -45
        elif angle > 45:
            angle = 45
        ms = (angle / 45) * 0.5 + 1.5
    return floor(ms * 1000000)

servo = PWM(Pin(11))
servo.freq(100)

esc = PWM(Pin(15))
esc.freq(100)

print("Arming the ESC!")
arm_esc(esc)
print("ESC is armed.")
sleep(0.5)

print("Turning servo and setting speed to minimum")
servo.duty_ns(convert_angle(30))
esc.duty_u16(convert_speed(0.1))
sleep(3)

print("Resetting steering angle and disabling PWM pins")
servo.duty_ns(1500000)
sleep(0.02)
servo.deinit()
esc.deinit()