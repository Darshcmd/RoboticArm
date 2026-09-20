# Gesture-Controlled 5-DOF Robotic Arm using Computer Vision

https://www.youtube.com/watch?v=PDEdxRVkMdo

---

## What This Is, and Why I Built It

I built a gesture-controlled, 3D-printable, 5-degrees-of-freedom, desktop-sized robotic arm. The arm is actuated by three standard servos and two micro servos, and it mimics my arm movements in real time. I detect my arm pose with a plain webcam using OpenCV colour tracking, compute the joint angles in Python, and stream them to an Arduino Uno over serial.

I made the three colour markers I wear on my wrist, elbow, and tricep out of LEGO pieces and velcro tape — nothing fancy, just something that catches the camera's eye.

This was originally a project by Jingzhou Liu. I forked it and kept building on it: upgrading the servo driver, adding a proper claw end effector, adding base rotation, improving the vision pipeline so it's more reliable, and making the colour tuning much easier when the lighting changes.

---

## What I Changed

Here's what I actually touched compared to the original project:

- **Upgraded to a PCA9685 servo driver.** The original used direct Arduino PWM pins. I moved to a PCA9685 16-channel PWM board so all five servos get clean, consistent PWM at 60 Hz without eating up the Arduino's timers. That also lets me remap channels easily if I rewire the arm.
- **Added a real end effector (claw).** The original didn't have a working gripper. I added the fifth servo as a claw, fully controlled from the Python side. Press E to open and close it.
- **Added base rotation.** The original arm couldn't rotate its base. I added a base servo and made it controllable with the SPACE bar — each press rotates the base by 45 degrees.
- **Rewrote the serial protocol to be robust.** The original sent three raw angle bytes. I switched to a framed protocol with a sync byte (0xAA), five angle bytes (arm1, arm2, tilt, base, claw), range checks on the Arduino side, and an ACK back from the Arduino so the host can verify delivery. Corrupted bytes can't slip through anymore.
- **Improved the vision pipeline.** I added a Haar cascade face detector that blanks the face out of every colour mask so the camera doesn't get confused by my face. I added roundness filtering so background junk blobs get rejected. I added exponential smoothing on all joint angles to kill jitter. I added a separate masks debug window so I can see exactly which pixels each colour filter is picking up.
- **Made colour calibration way easier for a new environment.** I wrote two calibration tools. `hsv_tune.py` is an interactive trackbar tuner that loads the current values as presets, so I can tweak a colour and save it in seconds. `auto_hsv.py` is fully automatic — I hold the marker in front of the camera, it captures 30 frames, finds the dominant colour cluster, and prints tight HSV bounds. Both are designed for when I move the arm to a new room or the lighting changes.
- **Added a PCA9685 channel diagnostic sketch** so I can verify which channel each servo is actually on — useful when I rewire the arm.
- **Added a proper serial link verification test** — `test_serial.py` sends the startup pose, probes the old protocol, then sweeps the base and claw with the new protocol and prints what it sent. `probe_channels.py` reads the firmware banner and ACKs so I can prove what the Arduino actually executed.
- **Made the Arduino port auto-detect.** The Python side probes `/dev/cu.usb*` automatically. If there's no Arduino, it runs in vision-only mode instead of crashing.
- **Rewrote the README** in my own voice, with the demo video up top and in the middle, and a small practical start guide at the end.

---

## What Makes This Different

A few things I think set this apart from the original:

- The original was a 3-servo arm with no end effector and no base rotation. This one is a full 5-DOF arm with a working claw and a rotating base — that's two extra degrees of freedom that the original didn't have.
- The original sent three angle bytes over serial and hoped for the best. This one uses a framed, ACKed protocol with range checks — it's much harder to corrupt a command and have the arm do something unexpected.
- The original had no face handling, so if I leaned into the camera my face could get picked up as a marker. This one blanks the face out of every mask, which makes it far more reliable when I'm close to the camera.
- The original had one HSV tuner script. I have two — a manual trackbar one for fine control and a fully automatic one for quick recalibration when the lighting changes. That matters because colour tracking is the weak point of this whole approach; if the bounds are wrong nothing else works.
- The original drove servos directly from the Arduino's PWM pins. This one uses a PCA9685, which is the standard way people drive multiple servos now — cleaner, more channels, and it leaves the Arduino free to do other things.

---

## Demonstration

Here the arm in action — the vision pipeline tracking my arm markers and driving all five servos in real time:

https://www.youtube.com/watch?v=PDEdxRVkMdo

---

## Quick Start

### 0. Clone and enter the project

```bash
cd Gesture-Controlled-5-DOF-Robotic-Arm-using-Computer-Vision
```

### 1. (macOS) Grant terminal accessibility for global hotkeys (optional)

The optional global hotkeys use `pynput`, which on macOS needs screen recording and accessibility permission. If you skip this, the arm still works fully via the window keys, terminal keys, and clickable buttons.

```bash
sudo codesign --force --options runtime --sign - ./venv/bin/python
```

Then grant your terminal app (Terminal or iTerm) screen recording permission in **System Settings > Privacy & Security > Screen Recording** and **Accessibility**, and restart the terminal.

### 2. (Optional) Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Flash the Arduino firmware

Open `Gesture_Controlled_Robotic_Arm_Arduino_Code/Gesture_Controlled_Robotic_Arm_Arduino_Code.ino` in the Arduino IDE (or PlatformIO), select your board (Arduino Uno), and upload. Make sure the PCA9685 servo driver is wired to the Arduino via I2C (SDA/SCL) and powered separately with 5-6 V.

### 4. Verify the PCA9685 channel map (if unsure)

If you're not sure which PCA9685 channel is wired to which joint, upload `diag_test/diag_test.ino` and watch the arm. Each channel (0-5) sweeps in sequence so you can confirm the mapping before running the main firmware.

### 5. Tune the HSV colour bounds for your lighting

The arm tracks three coloured markers:

- **Yellow** on the tricep
- **Red** on the elbow
- **Green** on the wrist

Run the interactive tuner for each colour — adjust the trackbars until only that block is white in the mask, then press ESC:

```bash
./venv/bin/python hsv_tune.py yellow
./venv/bin/python hsv_tune.py red
./venv/bin/python hsv_tune.py green
```

Or use the fully automatic calibrator — hold the marker in front of the camera and it captures 30 frames, finds the dominant colour cluster, and prints tight bounds:

```bash
./venv/bin/python auto_hsv.py yellow
./venv/bin/python auto_hsv.py red
./venv/bin/python auto_hsv.py green
```

Copy the resulting lower/upper tuples into lines 15-22 of `Gesture_Controlled_Robotic_Arm_Python_Code.py`:

```python
greenLower  = (38, 95, 72);   greenUpper  = (96, 255, 255)
redLower    = (0, 122, 119);  redUpper    = (10, 255, 255)
yellowLower = (15, 119, 76);  yellowUpper = (29, 255, 255)
```

### 6. Verify the serial link

With the Arduino plugged in and the main sketch flashed, put the arm somewhere it can move freely, then run:

```bash
./venv/bin/python test_serial.py
```

The script sends the startup pose (arm should stay still), then does a base sweep and a claw sweep. Watch the arm and the printed ACKs to confirm everything moves as expected.

For a deeper verification that reads the firmware banner and every ACK, run:

```bash
./venv/bin/python probe_channels.py
```

### 7. Run the arm

```bash
./venv/bin/python Gesture_Controlled_Robotic_Arm_Python_Code.py
```

Stand so all three markers are visible, roughly arm's length from the camera. The `Frame` window shows the detected circles and vectors. Use **SPACE** to rotate the base, **E** to toggle the claw, **Q** to quit. You can also click the BASE, CLAW, and QUIT buttons on the video overlay.

If no Arduino is found, the program runs in vision-only mode — the tracking overlay still works, you just don't get servo movement.

---

## Summary

This is my gesture-controlled, 5-DOF, desktop-sized, 3D-printable robotic arm. It uses a standard webcam and three coloured markers (yellow on the tricep, red on the elbow, green on the wrist) to track my arm pose in real time with OpenCV, then maps that pose to the robotic arm over serial.

The arm is driven by an Arduino Uno talking to a PCA9685 servo driver board, which powers all five servos: base rotation, shoulder, elbow, wrist tilt, and a claw end effector. The vision pipeline runs on the host computer and sends joint angles to the Arduino only when they change.

What makes this my version rather than just a fork: I upgraded the serial link to a framed, ACKed protocol with range checks; I moved from direct Arduino PWM to a PCA9685 driver; I added base rotation and a working claw for two extra degrees of freedom; I added an automatic wrist tilt solver so the gripper stays level; I wrote two HSV calibration tools (one interactive, one fully automatic) so the colour tracking works when I move to a new room or the lighting changes; I added face exclusion and circularity-based marker filtering so the camera doesn't get confused; and I added EMA smoothing and a masks debug window so the whole thing is more accurate and easier to debug.

The result is a gesture-controlled robotic arm that actually works reliably in a new environment, with tools to retune the colour tracking when the lighting changes, and a clear way to verify the serial link and the PCA9685 channel mapping before running the arm.

