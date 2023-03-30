from machine import Pin, UART, PWM
import queue
import uasyncio
from time import sleep
from math import floor
'''
uart = UART(0, baudrate=9600, rx=Pin(1))

uart.init(bits=8, parity=None, stop=1)
led = Pin(25, Pin.OUT)

while True:
    if uart.any():
        data = uart.read()
        print(f'Received {data} over uart')
        if data == b'test':
            led.toggle()
    time.sleep(1)
'''

# Below this point is test code for UART combined with async event loop
led = Pin(25, Pin.OUT)
uart = UART(0, baudrate=9600, rx=Pin(1))
uart.init(bits=8, parity=None, stop=1)
last_was_reverse = False
servo = PWM(Pin(16))
servo.freq(100)

esc = PWM(Pin(15))
esc.freq(100)

def arm_esc():
    esc.duty_ns(2000000)
    sleep(0.02)
    esc.duty_ns(1000000)
    sleep(0.02)
    esc.duty_ns(1500000)
    sleep(0.5)

def set_motor(percent_speed, reverse=False):
    global last_was_reverse
    '''
    Accepts a number between 1-100 that represents the percent speed for the motor.
    Speed is bounded to 80% because higher is bad
    
    ms = 0.005 * percent_speed + 1.5
    '''
    if percent_speed > 80:
       percent_speed = 80
    if not last_was_reverse and not reverse:
        # Forward while currently going forward
        ms = 0.005 * percent_speed + 1.5
        print(f'Going forward. ms is {ms}')
        esc.duty_ns(floor(ms * 1000000))
    elif not last_was_reverse and reverse:
        # Reverse while currently going forward
        # Brake
        esc.duty_ns(floor((-0.005 * 20 + 1.5) * 1000000))
        sleep(0.02)
        
        set_neutral()
        sleep(0.04)
        
        ms = -0.005 * percent_speed + 1.5
        esc.duty_ns(floor(ms * 1000000))
        last_was_reverse = True
    elif last_was_reverse and reverse:
        # Reverse while currently going reverse
        ms = -0.005 * percent_speed + 1.5
        esc.duty_ns(floor(ms * 1000000))
    else:
        # Forward while currently going reverse
        # Brake
        esc.duty_ns(floor((0.005 * 20 + 1.5) * 1000000))
        sleep(0.02)
        
        set_neutral()
        sleep(0.04)
        
        ms = 0.005 * percent_speed + 1.5
        esc.duty_ns(floor(ms * 1000000))
        
        last_was_reverse = False

def set_neutral():
    esc.duty_ns(floor(1.5 * 1000000))

def set_steering(angle):
    pass

async def uart_handler(q):
    message = []
    print('Waiting for serial communication')
    while True:
        if uart.any():
            byte = uart.read(1)
            if byte == b'!':
                command = b''.join(message)
                #print(f'Final message is {command}')
                await q.put(command)
                message = []
            elif byte != b' ':
                message.append(byte)
        await uasyncio.sleep_ms(50)
            
async def main():
    event_queue = queue.Queue()
    
    arm_esc()
    
    uasyncio.create_task(uart_handler(event_queue))
    try:
        while True:
            print('Main is waiting on event queue')
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
    except:
        print('Exception in main loop')
        servo.deinit()
        esc.deinit()
        
uasyncio.run(main())
servo.duty_ns(1500000)
sleep(0.02)
servo.deinit()
esc.deinit()