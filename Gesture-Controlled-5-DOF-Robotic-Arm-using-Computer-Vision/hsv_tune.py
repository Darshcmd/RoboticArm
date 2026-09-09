"""HSV calibration tool (improved version of HSV.py).

Usage:
    ./venv/bin/python hsv_tune.py green
    ./venv/bin/python hsv_tune.py red
    ./venv/bin/python hsv_tune.py yellow

- Seeds the trackbars with sensible starting values for the chosen color.
- Continuously writes the current 6 values to /tmp/hsv_<color>.log
  so another process can read them while you tune.
- Press ESC (with the image window focused) to finish; values print here too.
"""
import sys
import cv2
import numpy as np

PRESETS = {
    'green':  dict(h=38, s=95,  v=72,  h1=96,  s1=255, v1=255),
    'red':    dict(h=0,  s=122, v=119, h1=10,  s1=255, v1=255),
    'yellow': dict(h=15, s=115, v=72,  h1=27,  s1=174, v1=255),
}

color = sys.argv[1].lower() if len(sys.argv) > 1 else 'green'
if color not in PRESETS:
    print(f'Unknown color "{color}". Choose from: {", ".join(PRESETS)}')
    sys.exit(1)

out_path = f'/tmp/hsv_{color}.log'
open(out_path, 'w').close()  # truncate

cap = cv2.VideoCapture(0)


def nothing(arg):
    pass


# takes an image, and a lower and upper bound
# returns only the parts of the image in bounds
def only_color(frame, color_ranges, morph):
    h, s, v, h1, s1, v1 = color_ranges
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([h, s, v])
    upper = np.array([h1, s1, v1])
    mask = cv2.inRange(hsv, lower, upper)
    res = cv2.bitwise_and(frame, frame, mask=mask)
    return res, mask


# setup trackbars
cv2.namedWindow('image')
for key in ('h', 's', 'v', 'h1', 's1', 'v1'):
    cv2.createTrackbar(key, 'image', PRESETS[color][key], 255, nothing)

print(f'Tuning "{color}" — adjust trackbars until ONLY the {color} block is white in the mask.')
print('Press ESC to finish. Values are being saved to', out_path)

# main loop of the program
while True:
    _, img = cap.read()
    if img is None:
        continue

    h = cv2.getTrackbarPos('h', 'image')
    s = cv2.getTrackbarPos('s', 'image')
    v = cv2.getTrackbarPos('v', 'image')
    h1 = cv2.getTrackbarPos('h1', 'image')
    s1 = cv2.getTrackbarPos('s1', 'image')
    v1 = cv2.getTrackbarPos('v1', 'image')

    img, mask = only_color(img, (h, s, v, h1, s1, v1), 0)

    cv2.imshow('img', img)
    cv2.imshow('image', mask)

    # save current values continuously so they can be read while tuning
    with open(out_path, 'w') as f:
        f.write(f'{h},{s},{v},{h1},{s1},{v1}\n')

    k = cv2.waitKey(1) & 0xFF
    if k == 27:
        break

print(f'FINAL h,s,v,h1,s1,v1 = {h},{s},{v},{h1},{s1},{v1}')
cap.release()
cv2.destroyAllWindows()
