#include <Servo.h>
Servo myservo;
#define rouge 4
#define verte 5
#define servo 9

int action;
int pos = 0;
int place = 5;  // Nombre de places initiales
unsigned long previousMillis = 0;
void setup() {
  myservo.attach(servo);
  pinMode(rouge, OUTPUT);
  pinMode(verte, OUTPUT);
  Serial.begin(9600);
  myservo.write(90);
  digitalWrite(verte,0);
  digitalWrite(rouge,1);
  delay(2000);  // Adjust the delay as needed

}

void loop() {

  digitalWrite(rouge, LOW);
  if (Serial.available()) {
    action = Serial.parseInt();
    if (action == 1) {
     
      openBarrier();
      digitalWrite(verte,1);
      digitalWrite(rouge,0);
      
      delay(4000);
      digitalWrite(verte,0);
      digitalWrite(rouge,1);
      closeBarrier();
      delay(4000);
    }
    if (action == -1 ) {
      
    }
    if (action == 0 ) {
      
    }

  }

}

void openBarrier() {
  for (pos = 0; pos <= 90; pos += 1) {
    myservo.write(pos);
    delay(15);
  }
}

void closeBarrier() {
  for (pos = 90; pos >= 0; pos--) {
    myservo.write(pos);
    delay(15);
  }
}
