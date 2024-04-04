/*
  BlinkRGB

  Demonstrates usage of onboard RGB LED on some ESP dev boards.

  Calling digitalWrite(RGB_BUILTIN, HIGH) will use hidden RGB driver.
    
  RGBLedWrite demonstrates controll of each channel:
  void neopixelWrite(uint8_t pin, uint8_t red_val, uint8_t green_val, uint8_t blue_val)

  WARNING: After using digitalWrite to drive RGB LED it will be impossible to drive the same pin
    with normal HIGH/LOW level
*/
//#define RGB_BRIGHTNESS 64 // Change white brightness (max 255)

// the setup function runs once when you press reset or power the board

void setup() {
  Serial.begin(9600);
  // No need to initialize the RGB LED
}

// the loop function runs over and over again forever
void loop() {
#ifdef RGB_BUILTIN
  Serial.println("istart");
  digitalWrite(38, HIGH);   // Turn the RGB LED white
  delay(500);
  digitalWrite(38, LOW);    // Turn the RGB LED off
  delay(500);

  neopixelWrite(38,RGB_BRIGHTNESS,0,0); // Red
  delay(500);
  neopixelWrite(38,0,RGB_BRIGHTNESS,0); // Green
  delay(500);
  neopixelWrite(38,0,0,RGB_BRIGHTNESS); // Blue
  delay(500);
  neopixelWrite(38,0,0,0); // Off / black
  delay(500);
  Serial.println("iend");
#endif
}
