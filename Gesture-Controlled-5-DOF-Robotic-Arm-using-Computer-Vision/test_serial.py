"""Base and claw only test.
Sends protocol v2 packets."""
import struct
import time
import serial
import serial.tools.list_ports


def find_arduino():
    for p in serial.tools.list_ports.comports():
        if p.device.startswith('/dev/cu.usb'):
            return p.device
    return None


def new_packet(arm1, arm2, tilt, base, claw):
    return struct.pack('>BBBBBB', 0xAA, arm1, arm2, tilt, base, claw)


def old_packet(arm1, arm2, tilt):
    return struct.pack('>BBBB', 0xAA, arm1, arm2, tilt)


port = find_arduino()
if port is None:
    print('NO ARDUINO FOUND - plug it in and retry.')
    raise SystemExit(1)

print('Opening', port, '...')
ser = serial.Serial(port, 9600)
time.sleep(2.5)  # the Uno auto-resets when the port opens

print()
print('TEST 1 - legacy probe: nudging the SHOULDER with the OLD 3-angle protocol.')
print('   If the shoulder moves here but nothing moves later, the Arduino')
print('   still runs the OLD firmware and needs the new sketch uploaded.')
ser.write(old_packet(110, 74, 60))
time.sleep(2.0)
ser.write(old_packet(72, 74, 60))
time.sleep(2.0)

print()
print('TEST 2 - BASE: rotating the FIRST servo 90 -> 150 -> 90 -> 30 -> 90')
for base in (150, 90, 30, 90):
    ser.write(new_packet(72, 74, 60, base, 40))
    print('   base ->', base)
    time.sleep(2.0)

print()
print('TEST 3 - CLAW: opening/closing the LAST servo 40 -> 150 -> 40 -> 150')
for claw in (150, 40, 150, 40):
    ser.write(new_packet(72, 74, 60, 90, claw))
    print('   claw ->', claw)
    time.sleep(2.0)

ser.close()
print()
print('DONE - watch the arm and report exactly what moved.')

