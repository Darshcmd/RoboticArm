"""Firmware probe, ACK lines.
Watch base and claw move."""
import struct
import time
import serial
import serial.tools.list_ports


def find_arduino():
    for p in serial.tools.list_ports.comports():
        if p.device.startswith('/dev/cu.usb'):
            return p.device
    return None


port = find_arduino()
if port is None:
    print('NO ARDUINO FOUND')
    raise SystemExit(1)

print('Opening', port, '...')
ser = serial.Serial(port, 9600, timeout=0.2)
time.sleep(2.5)  # Uno auto-resets on port open

# Banner proves flashed firmware version
banner = ser.read(256).decode(errors='replace')
print('-- Arduino says on startup --')
print(banner.strip() if banner.strip() else '(no banner - OLD firmware still running!)')

def read_acks(duration):
    end = time.time() + duration
    got = []
    while time.time() < end:
        line = ser.readline().decode(errors='replace').strip()
        if line:
            print('   Arduino ACK:', line)
            got.append(line)
    return got


def pkt(base, claw):
    return struct.pack('>BBBBBB', 0xAA, 72, 74, 60, base, claw)


print()
print('>>> BASE sweep 90 -> 160 -> 20 -> 160 -> 90 - WATCH THE BASE')
for base in (160, 20, 160, 90):
    ser.write(pkt(base, 40))
    read_acks(2.2)

print()
print('>>> CLAW sweep 40 -> 150 -> 40 -> 150 - WATCH THE GRIPPER')
for claw in (150, 40, 150, 40):
    ser.write(pkt(90, claw))
    read_acks(2.2)

ser.close()
print()
print('VERIFICATION DONE - ACK lines above prove what the Arduino executed.')

