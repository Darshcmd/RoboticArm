"""Auto HSV calibration, no GUI needed.
Usage: ./venv/bin/python auto_hsv.py yellow"""
import sys
import time
import cv2
import numpy as np

HUE_FAMILIES = {
    # hue range plus minimum saturation
    'green':  (35, 90, 80, 80),
    'yellow': (12, 45, 140, 100),
    'red':    (0, 10, 140, 100),   # low-red side
    'red_hi': (165, 179, 140, 100) # high-red side (wrap)
}

color = sys.argv[1].lower() if len(sys.argv) > 1 else 'yellow'
if color not in HUE_FAMILIES:
    print(f'Unknown color "{color}". Choose from: {", ".join(HUE_FAMILIES)}')
    sys.exit(1)

hue_lo, hue_hi, sat_min, val_min = HUE_FAMILIES[color]

def to_bgr(frame):
    """Normalize any frame layout to 3-channel BGR."""
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if frame.shape[2] == 1:
        return cv2.cvtColor(frame[:, :, 0], cv2.COLOR_GRAY2BGR)
    if frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return frame


cap = cv2.VideoCapture(0)
frames = []
print(f'Capturing 30 frames for "{color}"...')
while len(frames) < 30:
    ok, frame = cap.read()
    if not ok:
        continue
    frame = to_bgr(frame)
    frame = cv2.GaussianBlur(frame, (11, 11), 0)
    frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
    time.sleep(0.1)
cap.release()

pix = np.concatenate([f.reshape(-1, 3) for f in frames])
h_all, s_all, v_all = pix[:, 0], pix[:, 1], pix[:, 2]

# bright candidate pixels in hue family
mask = (h_all >= hue_lo) & (h_all <= hue_hi) & (s_all > sat_min) & (v_all > val_min)

count = int(mask.sum())
print(f'Candidate pixels found: {count}')
if count < 5000:
    print('FAILED: not enough colored pixels - bring the marker closer / improve lighting.')
    sys.exit(2)

# peak of hue histogram wins
# band plus minus 8 hue
cand_h = h_all[mask]
hist, edges = np.histogram(cand_h, bins=hue_hi - hue_lo + 1, range=(hue_lo, hue_hi + 1))
peak_bin = int(np.argmax(hist))
peak_hue = (edges[peak_bin] + edges[peak_bin + 1]) / 2
print(f'Dominant hue: {peak_hue:.1f} (band {edges[peak_bin]:.0f}-{edges[peak_bin+1]:.0f}, {hist[peak_bin]} px)')

band_mask = mask & (np.abs(h_all.astype(int) - peak_hue) <= 8)
h_vals = h_all[band_mask]
s_vals = s_all[band_mask]
v_vals = v_all[band_mask]
print(f'Dominant cluster pixels: {len(h_vals)} ({len(h_vals)/count*100:.0f}% of candidates)')

# Robust bounds via percentiles, slightly padded
h_l, h_h = np.percentile(h_vals, [3, 97])
s_l, s_h = np.percentile(s_vals, [2, 98])
v_l, v_h = np.percentile(v_vals, [2, 98])

h_l = max(0, int(h_l) - 3)
h_h = min(179, int(h_h) + 3)
s_l = max(0, int(s_l) - 25)
s_h = 255
v_l = max(0, int(v_l) - 25)
v_h = 255

lower, upper = (h_l, s_l, v_l), (h_h, s_h, v_h)
print(f'Lower {lower}  Upper {upper}')

# sanity check on live frame
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()
if ok:
    frame = to_bgr(frame)
    hsv = cv2.cvtColor(cv2.GaussianBlur(frame, (11, 11), 0), cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, np.array(lower), np.array(upper))
    coverage = m.mean() / 255 * 100
    print(f'Mask coverage in a live frame: {coverage:.2f}% of image')
    if coverage > 15:
        print('WARNING: mask covers a lot of the frame - bounds may be too loose.')

with open(f'/tmp/hsv_{color}.log', 'w') as f:
    f.write(f'{lower[0]},{lower[1]},{lower[2]},{upper[0]},{upper[1]},{upper[2]}\n')
print(f'Saved to /tmp/hsv_{color}.log')
