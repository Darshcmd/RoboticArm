// PCA9685 channel sweep — drives channels 0..5 ONE AT A TIME so you can
// identify which channel is connected to which joint of the arm.
// Order: ch0 -> ch1 -> ch2 -> ch3 -> ch4 -> ch5 (two sweeps each).
// LED is ON while a channel is being swept.
#include <Adafruit_PWMServoDriver.h>
#include <Wire.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

const int CHANNELS = 6;
const int PULSE_MIN = 150;  // ~0 deg at 60Hz
const int PULSE_MAX = 600;  // ~180 deg at 60Hz

int angleToPulse(int angle) {
  int pulse = map(angle, 0, 180, PULSE_MIN, PULSE_MAX);
  pulse = constrain(pulse, PULSE_MIN, PULSE_MAX);
  return pulse;
}

void sweepChannel(int ch) {
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.print("TESTING CHANNEL ");
  Serial.println(ch);
  // two sweeps 72 -> 110 -> 72
  for (int cycle = 0; cycle < 2; cycle++) {
    for (int pos = 72; pos <= 110; pos += 3) { pwm.setPWM(ch, 0, angleToPulse(pos)); delay(25); }
    for (int pos = 110; pos >= 72; pos -= 3) { pwm.setPWM(ch, 0, angleToPulse(pos)); delay(25); }
  }
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
}

void setup() {
  Wire.begin();
  Serial.begin(9600);
  Serial.println("PCA9685 DIAG START");
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);  // typical for clone boards
  pwm.setPWMFreq(60);
  delay(100);
  pinMode(LED_BUILTIN, OUTPUT);
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_BUILTIN, HIGH); delay(150);
    digitalWrite(LED_BUILTIN, LOW);  delay(150);
  }
}

void loop() {
  for (int ch = 0; ch < CHANNELS; ch++) {
    sweepChannel(ch);
  }
  Serial.println("CYCLE DONE - repeating");
  delay(1000);
}
