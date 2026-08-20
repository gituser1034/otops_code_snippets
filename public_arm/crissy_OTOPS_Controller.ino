// Crissy, Nouwen, Ayush, Olly, maybe others (lots worked on this file)
// Mega 5-stepper + 5-encoder (4 ext interrupts + 1 polled) + BMP280 + MPU6050 + GPS
// Libraries required: Adafruit_BMP280, Adafruit_Sensor

// Install on Jetson
// python3 -m pip install pyserial

#include <Wire.h>
#include <SoftwareSerial.h>
#include <ArduinoJson.h>
// #include <Adafruit_BMP280.h>
// #include <ArduinoJson.h>

// CONFIG MOTORS
const int NUM_MOTORS = 5;
//const uint32_t DEFAULT_STEP_INTERVAL_US = 1000;
const uint32_t STEPS = 1000;
const uint16_t STEP_PULSE_US = 5000;

const int STEP_PINS[NUM_MOTORS]   = {48, 44, 38, 36, 32}; 
const int DIR_PINS[NUM_MOTORS]    = {46, 42, 40, 34, 30};

//const int ENABLE_PINS[NUM_MOTORS] = {24, 27, 30, 33, 36, 29};

// Encoder pins
// ENC_A 0..3 use external interrupts on Mega pins 2,3,18,19
// ENC_A4 uses D50 and is polled to avoid I2C conflict (20 & 21 are used for I2C)

/*
const int ENC_A_PINS[NUM_MOTORS] = {2, 3, 18, 19, 50}
const int ENC_B_PINS[NUM_MOTORS] = {40, 41, 42, 43, 44};
*/

// Sensors / GPS pins
const int GPS_PPS = 49;
const int GPS_RX  = 10;
const int GPS_TX  = 11;
const int SOIL_PIN = A0;
const int AIR_PIN  = A3; // add more as required

// GLOBALS
//Motor Variables
volatile long encoderCount[NUM_MOTORS] = {0};
volatile long remainingSteps[NUM_MOTORS] = {0};
long currentPos[NUM_MOTORS] = {0};
int dirState[NUM_MOTORS] = {1,1,1,1,1};
bool motorActive[NUM_MOTORS] = {false};

unsigned long nextStepTimeUs[NUM_MOTORS] = {0};
uint32_t stepIntervalUs[NUM_MOTORS] = {STEPS, STEPS, STEPS, STEPS, STEPS};

// Sensor Init
SoftwareSerial gpsSerial(GPS_RX, GPS_TX);
// Adafruit_BMP280 bmp;

unsigned long lastSensorMillis = 0;
const unsigned long SENSOR_INTERVAL = 1000;


void setup() {
  Serial.begin(115200);
  Wire.begin(); // Mega: SDA=D20, SCL=D21

  for (int i = 0; i < NUM_MOTORS; ++i) {
    pinMode(STEP_PINS[i], OUTPUT);
    pinMode(DIR_PINS[i], OUTPUT);
    //pinMode(ENABLE_PINS[i], OUTPUT);
    digitalWrite(STEP_PINS[i], LOW);
    //digitalWrite(ENABLE_PINS[i], LOW);
    motorActive[i] = false;
    remainingSteps[i] = 0;
    nextStepTimeUs[i] = micros();
  }

  gpsSerial.begin(9600);
  pinMode(GPS_PPS, INPUT);
}

// This function written by Olly, minor modifications by Crissy
void recieve_command(){
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, line);

    if (err) {
      Serial.println("JSON parse failed");
      return;
    }
    
    float wrist = doc["wrist"];     // 0
    float gripper = doc["gripper"]; // 1
    float rotate = doc["rotate"];   // 2
    float base = doc["base"];       // 3
    float elbow = doc["elbow"];     // 4
    
    // Stops arm from moving on its own due to joystick drift
    float deadzone = 0.05;

    if (wrist > deadzone) {
      remainingSteps[0] = 500;
      dirState[0] = 1;
      motorActive[0] = true;
      nextStepTimeUs[0] = micros();
    } else if (wrist < -deadzone) {
      remainingSteps[0] = 500;
      dirState[0] = -1;
      motorActive[0] = true;
      nextStepTimeUs[0] = micros();
    } else {
      remainingSteps[0] = 0;
      motorActive[0] = false;
    }

    if (gripper > deadzone) {
      remainingSteps[1] = 500;
      dirState[1] = 1;
      motorActive[1] = true;
      nextStepTimeUs[1] = micros();
    } else if (gripper < -deadzone) {
      remainingSteps[1] = 500;
      dirState[1] = -1;
      motorActive[1] = true;
      nextStepTimeUs[1] = micros();
    } else {
      remainingSteps[1] = 0;
      motorActive[1] = false;
    }

    if (rotate > deadzone) {
      remainingSteps[2] = 500;
      dirState[2] = 1;
      motorActive[2] = true;
      nextStepTimeUs[2] = micros();
    } else if (rotate < -deadzone) {
      remainingSteps[2] = 500;
      dirState[2] = -1;
      motorActive[2] = true;
      nextStepTimeUs[2] = micros();
    } else {
      remainingSteps[2] = 0;
      motorActive[2] = false;
    }

    if (base > deadzone) {
      remainingSteps[3] = 500;
      dirState[3] = 1;
      motorActive[3] = true;
      nextStepTimeUs[3] = micros();
    } else if (base < -deadzone) {
      remainingSteps[3] = 500;
      dirState[3] = -1;
      motorActive[3] = true;
      nextStepTimeUs[3] = micros();
    } else {
      remainingSteps[3] = 0;
      motorActive[3] = false;
    }

    if (elbow > deadzone) {
      remainingSteps[4] = 500;
      dirState[4] = 1;
      motorActive[4] = true;
      nextStepTimeUs[4] = micros();
    } else if (elbow < -deadzone) {
      remainingSteps[4] = 500;
      dirState[4] = -1;
      motorActive[4] = true;
      nextStepTimeUs[4] = micros();
    } else {
      remainingSteps[4] = 0;
      motorActive[4] = false;
    }
  }
}

// previously had a large chunk of code for sensors, hidden

void printMotorStatus() {
  for (int i = 0; i < NUM_MOTORS; ++i) {
    Serial.print("M"); Serial.print(i);
    Serial.print(":POS="); Serial.print(currentPos[i]);
    //Serial.print(",REM="); Serial.print(remainingSteps[i]);
    Serial.print(",DIR="); Serial.print(dirState[i] > 0 ? "F" : "R");
    Serial.print(",ACT="); Serial.println(motorActive[i] ? "1" : "0");
  }
}

// MAIN LOOP
void loop() {

  recieve_command();

  uint32_t nowUs = micros();

  for (int i = 0; i < NUM_MOTORS; ++i) {
    if (motorActive[i] && remainingSteps[i] > 0) {

      if ((long)(nowUs - nextStepTimeUs[i]) >= 0) { //
        digitalWrite(DIR_PINS[i], dirState[i] > 0 ? HIGH : LOW);
        digitalWrite(STEP_PINS[i], HIGH);
        delayMicroseconds(STEP_PULSE_US);
        digitalWrite(STEP_PINS[i], LOW);

        remainingSteps[i]--;
        currentPos[i] += (dirState[i] > 0 ? 1 : -1);

        nextStepTimeUs[i] = micros() + stepIntervalUs[i];

        if (remainingSteps[i] == 0) {
          motorActive[i] = false;
          long enc = encoderCount[i];
          Serial.print("DONE:");
          Serial.print(i);
          Serial.print(",POS:");
          Serial.print(currentPos[i]);
          Serial.print(",ENC:");
          Serial.println(enc);
        }
      }
    }
  }
}
