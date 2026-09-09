// Gesture-Controlled 5-DOF Robotic Arm — PCA9685 version
// Serial protocol: 0xAA sync byte + 3 angle bytes (arm1, arm2, tilt).
// The sync byte makes byte-misalignment impossible to command garbage.
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

/*--------- PCA9685 channel mapping (verified by diag sweep) ---------*/
#define CH_BASE  0
#define CH_ARM1  1   // shoulder
#define CH_ARM2  2   // elbow
#define CH_WRIST 3
#define CH_TILT  4
#define CH_CLAW  5
/*-------------------------------------------------------------------*/

const byte SYNC_BYTE = 0xAA;
const int PULSE_MIN = 150;  // ~0 deg at 60Hz
const int PULSE_MAX = 600;  // ~180 deg at 60Hz

/*----------------The following values are the initial servo values----------------*/
int base_angle = 90;
int arm1_angle = 72;
int arm2_angle = 74;
int tilt_angle = 60;
/*---------------------------------------------------------------------------------*/

int angleToPulse(int angle) {
  int pulse = map(angle, 0, 180, PULSE_MIN, PULSE_MAX);
  return constrain(pulse, PULSE_MIN, PULSE_MAX);
}

void setup() {
  Wire.begin();
  Serial.begin(9600);
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);  // typical for clone PCA9685 boards
  pwm.setPWMFreq(60);
  delay(100);

  pwm.setPWM(CH_BASE,  0, angleToPulse(base_angle));
  pwm.setPWM(CH_ARM1,  0, angleToPulse(arm1_angle));
  pwm.setPWM(CH_ARM2,  0, angleToPulse(arm2_angle));
  pwm.setPWM(CH_TILT,  0, angleToPulse(tilt_angle));
}

void loop() {
  // Scan for the sync byte, then read the 3 angle bytes.
  while (Serial.available()) {
    if (Serial.peek() != SYNC_BYTE) {
      Serial.read();          // discard until we find a sync byte
      continue;
    }
    if (Serial.available() < 4) break;  // wait for the full packet

    Serial.read();            // consume sync byte
    int arm1 = Serial.read();
    int arm2 = Serial.read();
    int tilt = Serial.read();

    // sanity range check (belt and braces)
    if (arm1 <= 180 && arm2 <= 180 && tilt <= 180) {
      arm1_angle = arm1;
      arm2_angle = arm2;
      tilt_angle = tilt;
      pwm.setPWM(CH_ARM1, 0, angleToPulse(arm1_angle));
      pwm.setPWM(CH_ARM2, 0, angleToPulse(arm2_angle));
      pwm.setPWM(CH_TILT, 0, angleToPulse(tilt_angle));
    }
  }
}
