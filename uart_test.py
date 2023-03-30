from machine import Pin, UART
import queue
import uasyncio
'''
uart = UART(0, baudrate=9600, tx=Pin(0))

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

async def uart_handler(q):
    message = []
    print('Waiting for serial communication')
    while True:
        if uart.any():
            byte = uart.read(1)
            if byte == b'!':
                command = b''.join(message)
                print(f'Final message is {command}')
                await q.put(command)
                message = []
            else:
                message.append(byte)
        await uasyncio.sleep_ms(50)
            
async def main():
    event_queue = queue.Queue()
    
    uasyncio.create_task(uart_handler(event_queue))
    while True:
        print('Main is waiting on event queue')
        command = await event_queue.get()
        print(f'Main has recieved command {command}')
        if command == b'light':
            led.toggle()
            command = None

uasyncio.run(main())