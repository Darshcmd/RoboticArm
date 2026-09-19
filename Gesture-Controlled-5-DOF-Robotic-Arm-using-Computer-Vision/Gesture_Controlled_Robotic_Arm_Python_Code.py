"""Gesture arm vision pipeline.
SPACE base, E claw, Q quit."""
from imutils.video import VideoStream
import numpy as np
import cv2, imutils, time, serial, struct, math

try:
	from pynput import keyboard
	PYNPUT_OK = True
except Exception:
	PYNPUT_OK = False


def theta(v, w):
	return np.arccos(np.clip(v.dot(w) / (np.linalg.norm(v) * np.linalg.norm(w)), -1.0, 1.0))


def best_marker(cnts, min_area=300, min_circularity=0.35):
	"""Biggest round marker blob."""
	best, best_area = None, 0.0
	for c in cnts:
		area = cv2.contourArea(c)
		if area < min_area:
			continue
		perimeter = cv2.arcLength(c, True)
		circularity = 4 * math.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
		if circularity < min_circularity:
			continue
		if area > best_area:
			best, best_area = c, area
	return best


def marker_center(mask, frame):
	"""Marker center plus debug dot."""
	cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnts = imutils.grab_contours(cnts)
	c = best_marker(cnts)
	if c is None:
		return None
	((x, y), radius) = cv2.minEnclosingCircle(c)
	if radius <= 10:
		return None
	M = cv2.moments(c)
	center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
	cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
	cv2.circle(frame, center, 5, (0, 0, 255), -1)
	return center


arm2_angle = 74
arm1_angle = 72

# HSV bounds, project values
greenLower  = (38, 95, 72);   greenUpper  = (96, 255, 255)
redLower    = (0, 122, 119);  redUpper    = (10, 255, 255)
yellowLower = (15, 119, 76);  yellowUpper = (29, 255, 255)

# Servo config
BASE_START = 90    # startup base angle
BASE_STEP  = 45    # base degrees per press
CLAW_OPEN   = 120  # claw open angle
CLAW_CLOSED = 10   # claw closed angle

vs = VideoStream(src=0).start()
time.sleep(2.0)

# Arduino link, protocol v2
# Port auto detected
import serial.tools.list_ports


def find_arduino():
	for p in serial.tools.list_ports.comports():
		if p.device.startswith('/dev/cu.usb'):
			return p.device
	return None


arduino = None
_arduino_port = find_arduino()
if _arduino_port is None:
	print("WARNING: no Arduino found (no /dev/cu.usb* device) - vision-only mode.")
else:
	try:
		arduino = serial.Serial(_arduino_port, 9600)
		time.sleep(2.5)  # Uno resets on port open
		print("Arduino connected on", _arduino_port)
	except serial.SerialException as e:
		print("WARNING: could not open", _arduino_port, "-", e)
		print("Is another copy of this program still running? It holds the port.")
		print("Continuing in vision-only mode - commands will NOT reach the arm.")

base_angle = BASE_START
claw_angle = CLAW_CLOSED
quit_requested = False
last_hotkey = {}  # key times for dedupe

Horizontal_Vector = np.array([-10, 0])
Arm2_Vector = np.array([0, 0.1])
Arm1_Vector = np.array([0, 0.1])

# Smoothed angles match startup
arm1_smooth = float(arm1_angle)
arm2_smooth = float(arm2_angle)
tilt_smooth = 60.0
s1, s2, st = int(arm1_angle), int(arm2_angle), 60
last_sent = None

# Face detector blanks face zones
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Shared actions for inputs
def rotate_base():
	global base_angle
	base_angle = (base_angle + BASE_STEP) % 180
	print("Base rotated to {} degrees".format(base_angle))


def toggle_claw():
	global claw_angle
	claw_angle = CLAW_CLOSED if claw_angle == CLAW_OPEN else CLAW_OPEN
	print("Claw toggled to {} degrees".format(claw_angle))


# Global hotkeys need permission
def on_press(key):
	global quit_requested
	if key == keyboard.Key.space:
		rotate_base()
		last_hotkey['space'] = time.time()
	elif getattr(key, 'char', None) == 'e':
		toggle_claw()
		last_hotkey['claw'] = time.time()
	elif getattr(key, 'char', None) == 'q':
		quit_requested = True


key_listener = None
if PYNPUT_OK:
	try:
		key_listener = keyboard.Listener(on_press=on_press)
		key_listener.start()
		print("Global hotkeys active: SPACE = base, E = claw, Q = quit")
	except Exception:
		PYNPUT_OK = False
		print("pynput unavailable - use keys on the Frame window instead")

# On video buttons
# Mouse beats key focus
BTN_BASE = (10, 80, 210, 132)    # (x1, y1, x2, y2)
BTN_CLAW = (220, 80, 430, 132)
BTN_QUIT = (440, 80, 560, 132)


def on_mouse(event, x, y, flags, param):
	global quit_requested
	if event != cv2.EVENT_LBUTTONDOWN:
		return
	if BTN_BASE[0] <= x <= BTN_BASE[2] and BTN_BASE[1] <= y <= BTN_BASE[3]:
		rotate_base()
	elif BTN_CLAW[0] <= x <= BTN_CLAW[2] and BTN_CLAW[1] <= y <= BTN_CLAW[3]:
		toggle_claw()
	elif BTN_QUIT[0] <= x <= BTN_QUIT[2] and BTN_QUIT[1] <= y <= BTN_QUIT[3]:
		quit_requested = True


cv2.namedWindow("Frame")
cv2.setMouseCallback("Frame", on_mouse)

# Terminal keys, reliable path
# OpenCV ignores keys on macOS
# Hotkeys blocked, Tk crashes
# So read terminal directly
import sys as _sys
import termios, tty, select

_stdin_keys = False
try:
	_old_termios = termios.tcgetattr(_sys.stdin)
	tty.setcbreak(_sys.stdin.fileno())
	_stdin_keys = True
	print()
	print("=" * 64)
	print("KEYS ACTIVE IN THIS TERMINAL:  SPACE = rotate base   E = claw   Q = quit")
	print("(click on the terminal first so it receives your keystrokes)")
	print("=" * 64)
except Exception:
	print("No terminal for keys - use the on-video buttons in the Frame window.")


def read_terminal_key():
	"""Terminal key read, nonblocking."""
	if not _stdin_keys:
		return None
	dr, _, _ = select.select([_sys.stdin], [], [], 0)
	if dr:
		return _sys.stdin.read(1)
	return None


def restore_terminal():
	if _stdin_keys:
		termios.tcsetattr(_sys.stdin, termios.TCSADRAIN, _old_termios)


# Restore terminal on exit
import signal


def _handle_signal(sig, frame):
	global quit_requested
	quit_requested = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


while True:
	frame = vs.read()

	# Resize, blur, convert HSV
	frame = imutils.resize(frame, width=800)
	blurred = cv2.GaussianBlur(frame, (11, 11), 0)
	hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

	# Build masks, erode dilate denoise
	green_mask = cv2.inRange(hsv, greenLower, greenUpper)
	green_mask = cv2.erode(green_mask, None, iterations=2)
	green_mask = cv2.dilate(green_mask, None, iterations=2)

	red_mask = cv2.inRange(hsv, redLower, redUpper)
	red_mask = cv2.erode(red_mask, None, iterations=2)
	red_mask = cv2.dilate(red_mask, None, iterations=2)

	yellow_mask = cv2.inRange(hsv, yellowLower, yellowUpper)
	yellow_mask = cv2.erode(yellow_mask, None, iterations=2)
	yellow_mask = cv2.dilate(yellow_mask, None, iterations=2)

	# Blank face from every mask
	# Downscaled detection for speed
	gray_small = cv2.cvtColor(imutils.resize(frame, width=400), cv2.COLOR_BGR2GRAY)
	scale = frame.shape[1] / 400.0
	faces = face_cascade.detectMultiScale(gray_small, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
	for (fx, fy, fw, fh) in faces:
		x1 = max(0, int(fx * scale - fw * scale * 0.3))
		y1 = max(0, int(fy * scale - fh * scale * 0.3))
		x2 = min(frame.shape[1], int((fx + fw) * scale + fw * scale * 0.3))
		y2 = min(frame.shape[0], int((fy + fh) * scale + fh * scale * 0.3))
		green_mask[y1:y2, x1:x2] = 0
		red_mask[y1:y2, x1:x2] = 0
		yellow_mask[y1:y2, x1:x2] = 0
		cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)

	green_center = marker_center(green_mask, frame)
	red_center = marker_center(red_mask, frame)
	yellow_center = marker_center(yellow_mask, frame)

	# Shoulder from yellow red vector
	if (red_center and yellow_center):
		Arm1_Vector = np.array([red_center[0] - yellow_center[0], red_center[1] - yellow_center[1]])

		if (np.linalg.norm(Arm1_Vector) > 80 and np.linalg.norm(Arm1_Vector) < 300):
			cv2.line(frame, red_center, yellow_center, (0, 255, 0), thickness=3, lineType=8)
			arm1_angle = theta(Arm1_Vector, Horizontal_Vector)
			arm1_angle = round(180 * arm1_angle / np.pi)

			if (Arm1_Vector[1] < 0):
				arm1_angle = arm1_angle * -1

			arm1_angle = arm1_angle - 18
			if (arm1_angle < 0):
				arm1_angle = 160
			elif (arm1_angle > 160):
				arm1_angle = 160
			elif (arm1_angle < 50):
				arm1_angle = 50

	# Elbow from green red vector
	if (green_center and red_center):
		Arm2_Vector = np.array([red_center[0] - green_center[0], red_center[1] - green_center[1]])

		if (np.linalg.norm(Arm2_Vector) > 100 and np.linalg.norm(Arm2_Vector) < 230):
			cv2.line(frame, green_center, red_center, (0, 255, 0), thickness=3, lineType=8)
			arm2_angle = theta(Arm2_Vector, Arm1_Vector)
			arm2_angle = round(180 * arm2_angle / np.pi)

			arm2_angle = arm2_angle - 16
			if (arm2_angle > 154):
				arm2_angle = 154
			elif (arm2_angle < 10):
				arm2_angle = 10

	# Send angles on change
	if (math.isnan(arm2_angle) == False and math.isnan(arm1_angle) == False):
		# Wrist solver keeps gripper level
		alpha = arm2_angle + 16
		beta = 180 - (arm1_angle + 18)
		tilt_angle = -1 * (180 - alpha - beta) + 60
		if (tilt_angle < 0):
			tilt_angle = 0

		# Smoothing removes frame jitter
		SMOOTH = 0.4  # 0 frozen, 1 raw
		arm1_smooth += SMOOTH * (arm1_angle - arm1_smooth)
		arm2_smooth += SMOOTH * (arm2_angle - arm2_smooth)
		tilt_smooth += SMOOTH * (tilt_angle - tilt_smooth)

		s1, s2, st = int(round(arm1_smooth)), int(round(arm2_smooth)), int(round(tilt_smooth))

	# Transmit only on change
	if (s1, s2, st, base_angle, claw_angle) != last_sent:
		print("Arm1: {}  |  Arm2: {}  |  Tilt: {}  |  Base: {}  |  Claw: {}".format(
			s1, s2, st, base_angle, claw_angle))
		# sync plus five angle bytes
		if arduino is not None:
			# drop firmware ACK lines
			arduino.reset_input_buffer()
			arduino.write(struct.pack('>BBBBBB', 0xAA, s1, s2, st, base_angle, claw_angle))
		last_sent = (s1, s2, st, base_angle, claw_angle)

	# Masks view, white means detected
	# Left green, middle red, right yellow
	mask_view = np.hstack([green_mask, red_mask, yellow_mask])
	for label, xoff in (("GREEN", 10), ("RED", 810), ("YELLOW", 1610)):
		cv2.putText(mask_view, label, (xoff, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 255, 2)
	cv2.imshow("Masks", cv2.resize(mask_view, (1200, int(mask_view.shape[0] * 1200 / mask_view.shape[1]))))

	# HUD plus clickable buttons
	claw_state = "OPEN" if claw_angle == CLAW_OPEN else "CLOSED"
	cv2.putText(frame, "BASE: {}  CLAW: {} ({})".format(base_angle, claw_angle, claw_state),
		(10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

	for (x1, y1, x2, y2), label in (
			(BTN_BASE, "BASE +45"),
			(BTN_CLAW, "CLAW: {}".format(claw_state)),
			(BTN_QUIT, "QUIT")):
		cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), -1)
		cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
		cv2.putText(frame, label, (x1 + 10, y1 + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
	cv2.putText(frame, "keys live in the TERMINAL: SPACE = base | E = claw | Q = quit (or use buttons)",
		(10, 152), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

	# Show frame
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF

	# Window keys, deduped
	if key == ord(" ") and time.time() - last_hotkey.get('space', 0) > 0.2:
		rotate_base()
	elif key == ord("e") and time.time() - last_hotkey.get('claw', 0) > 0.2:
		toggle_claw()

	# Terminal keys, reliable path
	tkey = read_terminal_key()
	if tkey == " ":
		rotate_base()
	elif tkey in ("e", "E"):
		toggle_claw()
	elif tkey in ("q", "Q"):
		quit_requested = True

	# Quit from any input
	if quit_requested or key == ord("q"):
		break


# Stop the camera video stream
vs.stop()
cv2.destroyAllWindows()
if key_listener is not None:
	key_listener.stop()
if arduino is not None:
	arduino.close()
restore_terminal()

