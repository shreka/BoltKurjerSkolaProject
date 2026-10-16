
#include <SoftwareSerial.h>
#include <string.h>
#include <ctype.h>

// ===========================
// BLUETOOTH HM-10
// ===========================

// Arduino RX = D10, TX = D11
SoftwareSerial bluetooth(11, 10);

// ===========================
// MOTOR DRIVER L298N
// ===========================

const int ENA = 6;
const int IN1 = 2;
const int IN2 = 3;

const int IN3 = 4;
const int IN4 = 5;
const int ENB = 7;

// Motor speed: 0-255
int motorSpeed = 180;

// ===========================
// BLUETOOTH MESSAGE
// ===========================

char message[33];
byte messageLength = 0;

unsigned long lastReceived = 0;
const unsigned long messageTimeout = 250;

// ===========================
// MOTOR CONTROL
// ===========================

void setSpeed() {
  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);
}

void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

// Move forward
void forward() {
  stopMotors();

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  setSpeed();
}

// Move backward
void backward() {
  stopMotors();

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  setSpeed();
}

// Turn left
void right() {
  stopMotors();

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  setSpeed();
}

// Turn right
void left() {
  stopMotors();

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  setSpeed();
}

// ===========================
// PROCESS RECEIVED COMMAND
// ===========================

void processCommand(const char* text) {

  char cmd[33];

  byte start = 0;

  while (text[start] == ' ' ||
         text[start] == '\t') {
    start++;
  }

  byte i = 0;

  while (text[start] != '\0' && i < 32) {
    cmd[i++] = toupper((unsigned char)text[start++]);
  }

  while (i > 0 &&
         (cmd[i - 1] == ' ' ||
          cmd[i - 1] == '\t')) {
    i--;
  }

  cmd[i] = '\0';

  if (strcmp(cmd, "FORWARD") == 0) {
    forward();
  }
  else if (strcmp(cmd, "BACK") == 0 ||
           strcmp(cmd, "BACKWARD") == 0) {
    backward();
  }
  else if (strcmp(cmd, "LEFT") == 0) {
    left();
  }
  else if (strcmp(cmd, "RIGHT") == 0) {
    right();
  }
  else if (strcmp(cmd, "STOP") == 0) {
    stopMotors();
  }
  else {
    return;
  }

  Serial.print("Motor command: ");
  Serial.println(cmd);
}

// ===========================
// PROCESS BLUETOOTH MESSAGE
// ===========================

void processMessage() {
  if (messageLength == 0) return;

  message[messageLength] = '\0';

  Serial.print("Received: ");
  Serial.println(message);

  processCommand(message);

  messageLength = 0;
}

// ===========================
// SETUP
// ===========================

void setup() {
  Serial.begin(9600);
  bluetooth.begin(9600);

  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  stopMotors();

  Serial.println("Arduino ready!");
}

// ===========================
// MAIN LOOP
// ===========================

void loop() {

  while (bluetooth.available()) {
    char c = bluetooth.read();

    if (c == '\n' || c == '\r') {
      processMessage();
      continue;
    }

    if (messageLength < 32) {
      message[messageLength++] = c;
    }

    lastReceived = millis();
  }

  // Process messages without newline
  if (messageLength > 0 &&
      millis() - lastReceived >= messageTimeout) {
    processMessage();
  }
}
