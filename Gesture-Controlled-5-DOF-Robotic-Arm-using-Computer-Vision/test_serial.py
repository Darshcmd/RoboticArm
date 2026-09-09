"""Quick test: verifies Python can talk to the arm's Arduino over serial.

Sends the startup angles first (arm should stay still), then nudges
arm1 to 90 and back to 72 — you should see the shoulder joint move.

Each packet is the 0xAA sync byte followed by three angle bytes,
exactly matching the protocol in the main Arduino sketch.
"""
import struct
import time
import serial

PORT = '/dev/cu.usbserial-130'

SYNC_BYTE = 0xAA
STARTUP = (72, 74, 60)   # arm1, arm2, tilt — matches Arduino sketch defaults
NUDGE   = (90, 74, 60)   # arm1 moved +18 degrees

print('Opening', PORT, '...')
with serial.Serial(PORT, 9600, timeout=1) as arduino:
    time.sleep(2.5)  # Arduino Uno auto-resets when the port opens

    print('Sending startup angles', STARTUP, '(arm should stay still)')
    arduino.write(struct.pack('>BBBB', SYNC_BYTE, *STARTUP))
    time.sleep(1.5)

    print('Nudging arm1 to', NUDGE[0], 'degrees — WATCH THE ARM')
    arduino.write(struct.pack('>BBBB', SYNC_BYTE, *NUDGE))
    time.sleep(1.5)

    print('Returning to', STARTUP)
    arduino.write(struct.pack('>BBBB', SYNC_BYTE, *STARTUP))
    time.sleep(1.5)

print('Serial test finished — if the arm moved, communication works!')
