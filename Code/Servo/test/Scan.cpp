#include <Dynamixel2Arduino.h>

#if defined(ARDUINO_OpenRB)  
  #define DXL_SERIAL Serial1
  #define DEBUG_SERIAL Serial
  const int DXL_DIR_PIN = -1;
#else
  #define DXL_SERIAL Serial1
  #define DEBUG_SERIAL Serial
  const int DXL_DIR_PIN = 2;
#endif

const float DXL_PROTOCOL_VERSION = 2.0;
Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);

// Liste des baudrates possibles (en bps)
const int baudrates[] = {9600, 57600, 115200, 1000000, 2000000, 3000000, 4000000, 4500000};
// Plage des ID à scanner
const uint8_t min_id = 0, max_id = 252; 

void setup() {
  delay(2000);
  DEBUG_SERIAL.begin(115200);
  while(!DEBUG_SERIAL);

  DEBUG_SERIAL.println("🔍 Détection du moteur...");
  
  for (int i = 0; i < sizeof(baudrates) / sizeof(baudrates[0]); i++) {
    int baud = baudrates[i];
    dxl.begin(baud);
    DEBUG_SERIAL.print("⏳ Test baudrate : ");
    DEBUG_SERIAL.println(baud);
    
    for (uint8_t id = min_id; id <= max_id; id++) {
      if (dxl.ping(id)) {
        DEBUG_SERIAL.print("✅ Moteur détecté à ID ");
        DEBUG_SERIAL.print(id);
        DEBUG_SERIAL.print(" avec baudrate ");
        DEBUG_SERIAL.println(baud);
        return;
      }
    }
  }

  DEBUG_SERIAL.println("❌ Aucun moteur détecté !");
}

void loop() {
  delay(1000);
}
