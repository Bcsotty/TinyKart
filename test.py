from machine import Pin
from time import sleep, ticks_ms

interrupt_flag = 0
debounce_time=0
pin = Pin(0, Pin.IN, Pin.PULL_UP)
led = Pin(25, Pin.OUT)

def callback(pin):
    global interrupt_flag, debounce_time
    if ticks_ms() - debounce_time > 500:
        interrupt_flag = 1
        debounce_time = ticks_ms()

pin.irq(trigger=Pin.IRQ_FALLING, handler=callback)

while True:
    if interrupt_flag == 1:
        print("Interrupt has occured")
        interrupt_flag = 0
        led.toggle()