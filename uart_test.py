from machine import Pin, UART, PWM
import queue
import uasyncio
from time import sleep
from math import floor

"""
This library assumes that we are using frequency of 100hz, and cycles are 10ms. This is what we
got from using the oscilliscope on the ESC and servo, so this shouldn't need to be adjusted.
"""

# Constants that shouldn't be adjusted. They have the nanoseconds for the different PWM signals 
# Second half of constants can be removed e.g. right, left, and straight but ideally would like to rename
# full_forward, full_reverse, and neutral to make sense for ESC and SERVO
FULL_FORWARD_NS, RIGHT_NS = 2000000
FULL_REVERSE_NS, LEFT_NS = 1000000
NEUTRAL_NS, STRAIGHT_NS = 1500000

# Initializing the UART, servo, and ESC pins. 
uart = UART(0, baudrate=9600, rx=Pin(1))
uart.init(bits=8, parity=None, stop=1)

servo = PWM(Pin(16))
servo.freq(100)
esc = PWM(Pin(15))
esc.freq(100)

last_was_reverse = False # Variable used for tracking which direction the RC car is currently going

def arm_esc():
    '''
    Arms the ESC

    Arms the ESC using the built in arming sequence of forward for 2 cycles, reverse for 2 cycles, and neutral for 500ms
    '''

    esc.duty_ns(FULL_FORWARD_NS)
    sleep(0.02)
    esc.duty_ns(FULL_REVERSE_NS)
    sleep(0.02)
    esc.duty_ns(NEUTRAL_NS)
    sleep(0.5)


def clear_brake_lockout() -> None:
    '''
    Clears the brake lockout for the motor

    This function will clear the brake lockout caused by switching from foward to reverse, or vice versa. Assumes that
    last_was_reverse has NOT been updated prior to function call. This takes about 80 ms.

    TODO
    - Need to see what braking distance is and how much power we should use for braking the car
    - We may be able to reduce the sleep after neutral to 3 cycles, need to test. Only 10ms difference if it can't be changed.
    '''

    braking_power = 20 # Percent power, e.g. 10 would be 10% of motor speed for braking

    if last_was_reverse:
        ms = 0.005 * braking_power + 1.5 
    else:
        ms = -0.005 * braking_power + 1.5

    ns = floor(ms * 1000000)

    # Apply braking power for 2 cycles
    esc.duty_ns(ns)
    sleep(0.02)

    # Apply neutral for 4 cycles
    esc.duty_ns(NEUTRAL_NS)
    sleep(0.04)


def set_motor(percent_speed, reverse=False):
    '''
    Sets the motor to a speed

    Accepts a number between 1-100 that represents the percent speed for the motor.
    If the percent speed is higher then 80%, it will be reduced to 80% to prevent the motor from being damaged.
    
    The ms for the PWM signal is calculated as follows:
    ms = 0.005 * percent_speed + 1.5

    TODO
    - We need to test and see minimum percent_speed that will actually move the motor. At lower percentages, the motor will be active
      but will not have enough force to move the wheels
    - Test and make sure changes still work compared to the original spaghetti code
    '''

    global last_was_reverse

    if percent_speed > 80:
       percent_speed = 80

    # XOR operation to see if we need to clear the brake lockout
    if last_was_reverse ^ reverse:
        clear_brake_lockout()

    if reverse:
        ms = -0.005 * percent_speed + 1.5
    else:
        ms = 0.005 * percent_speed + 1.5

    ns = floor(ms * 1000000)
    esc.duty_ns(ns)

    last_was_reverse = reverse


def set_neutral():
    '''
    Sets the motor to neutral
    '''

    esc.duty_ns(NEUTRAL_NS)


def set_steering(angle):
    '''
    Sets the steering angle for the servo

    Accepts an angle in degrees between [-23, 23] and will set the servo to that angle, with -23 being max right and 23 being max left. Follows
    the REP 103 standard from here: https://www.ros.org/reps/rep-0103.html
    '''

    pass


async def uart_handler(q):
    '''
    Handles UART communications

    This function accepts a shared queue and will continously loop reading from the UART pin one byte at a time, until a terminator is read.
    The terminator is set to !, so commands will all end with !. Once the terminator has been read, the stored command will be added to the
    shared queue and the function will loop again.
    '''
    
    message = []
    print('Waiting for serial communication')
    while True:
        if uart.any():
            byte = uart.read(1)
            if byte == b'!':
                command = b''.join(message)
                await q.put(command)
                message = []
            elif byte != b' ':
                message.append(byte)
        await uasyncio.sleep_ms(50)
            

async def main():
    '''
    Main function for the PICO

    This function will handle the processing of commands received from the UART handler, and will call the corresponding motor/servo function
    depending on the message received.

    TODO
    - We should add validation before calling set_motor() since it requires an int cast that can raise an error so it
      doesn't crash the whole program due to one bad command.
    '''

    event_queue = queue.Queue()
    
    arm_esc()
    
    uasyncio.create_task(uart_handler(event_queue))
    try:
        while True:
            command = await event_queue.get()
            print(f'Main has recieved command {command}')

            str_command = command.decode('UTF-8')
            cmd_type = str_command[0]

            if cmd_type == 'F':
                percent_speed = str_command[1:]
                print(f'Setting forward with speed {percent_speed}')
                set_motor(int(percent_speed))
            elif cmd_type == 'R':
                percent_speed = str_command[1:]
                print(f'Setting reverse with speed {percent_speed}')
                set_motor(int(percent_speed), True)
            elif cmd_type == 'S':
                angle = str_command[1:]
                print(f'Setting steering with angle {angle}')
            elif cmd_type == 'N':
                print(f'Setting motor to neutral')
                set_neutral()
            elif cmd_type == 'E':
                print('Exiting the main loop')
                break
            else:
                print(f'Received invalid command {str_command}')
    except:
        """
        General exception clause to ensure ESC and servo are properly deinitialized.
        Most likely exceptions would be KeyboardInterrupt, or ValueError if the int cast doesn't work"""
        print('Exception in main loop')
        servo.deinit()
        esc.deinit()

# Starts the main function
uasyncio.run(main())

# Resets servo to straight forward, and deinitalizes the PINs so ESC and servo stop taking commands.
servo.duty_ns(STRAIGHT_NS)
sleep(0.02)

servo.deinit()
esc.deinit()