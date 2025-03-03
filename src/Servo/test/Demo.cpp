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

// Importation des noms des registres de contrôle
using namespace ControlTableItem;

struct Motor {
  uint8_t id;
  int min_pos;
  int max_pos;
};

Motor moteurs[] = {
  {20,  673, 1900},
  {3,  2000, 2200},//2100 milieu
  {4,   850, 1050}//950 milieu
};

const int N_MOTEURS = sizeof(moteurs) / sizeof(moteurs[0]);

void setup() {
  delay(2000);
  DEBUG_SERIAL.begin(115200);
  while (!DEBUG_SERIAL);

  DEBUG_SERIAL.println("🔹 Initialisation des moteurs...");

  dxl.begin(57600);
  dxl.setPortProtocolVersion(DXL_PROTOCOL_VERSION);

  for (int i = 0; i < N_MOTEURS; i++) {
    uint8_t id = moteurs[i].id;
    if (dxl.ping(id)) {
      dxl.torqueOff(id);
      dxl.setOperatingMode(id, OP_POSITION);
      dxl.torqueOn(id);
      dxl.writeControlTableItem(ControlTableItem::PROFILE_VELOCITY, id, 30); // Correction ici
      DEBUG_SERIAL.print("✅ Moteur ID ");
      DEBUG_SERIAL.print(id);
      DEBUG_SERIAL.println(" initialisé !");
    } else {
      DEBUG_SERIAL.print("❌ Échec du ping du moteur ID ");
      DEBUG_SERIAL.println(id);
    }
  }
  DEBUG_SERIAL.println("🚀 Démarrage de la boucle !");
}

void loop() {
  for (int step = 0; step < 2; step++) {
    for (int i = 0; i < N_MOTEURS; i++) {
      uint8_t id = moteurs[i].id;
      int target_pos = (step == 0) ? moteurs[i].max_pos : moteurs[i].min_pos;

      dxl.setGoalPosition(id, target_pos);
      DEBUG_SERIAL.print("➡️ Moteur ID ");
      DEBUG_SERIAL.print(id);
      DEBUG_SERIAL.print(" → Position cible : ");
      DEBUG_SERIAL.println(target_pos);

      int present_position;
      do {
        present_position = dxl.getPresentPosition(id);
        DEBUG_SERIAL.print("   🏁 Moteur ID ");
        DEBUG_SERIAL.print(id);
        DEBUG_SERIAL.print(" Position actuelle : ");
        DEBUG_SERIAL.println(present_position);
        delay(100);
      } while (abs(target_pos - present_position) > 10);

      DEBUG_SERIAL.print("✅ Moteur ID ");
      DEBUG_SERIAL.print(id);
      DEBUG_SERIAL.println(" a atteint la position !");
    }
    delay(1000);
  }
}
