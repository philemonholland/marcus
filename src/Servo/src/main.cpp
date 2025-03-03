#include <Dynamixel2Arduino.h>
#include <Servo.h>



// Setup environnement dynamixel

#if defined(ARDUINO_OpenRB)  
  #define DXL_SERIAL Serial1 // OpenRB-150 uses Serial1 for Dynamixel
  #define PC_SERIAL Serial // USB Serial for PC communication

  const int DXL_DIR_PIN = -1;
  const float DXL_PROTOCOL_VERSION = 2.0;

  Dynamixel2Arduino dxl(DXL_SERIAL);
#else
  break; // Erreur pas la bonne carte
#endif




// Definition des ID moteurs dynamixel

int DXL_IDs[] = 
{

  3, // ID du moteur droit (To verify)
  4, // ID du moteur gauche (To verify)
  20 // ID du moteur rotation bas

}; // Peuvent etre brancher sur n'importe quel port dynamixel

const int N_DXL = sizeof(DXL_IDs) / sizeof(DXL_IDs[0]);




// Definition des ports des servo PWM


Servo Servos_PWM[6]
{
    Servo(), // Servo 0
    Servo(), // Servo 1
    Servo(), // Servo 2
    Servo(), // Servo 3
    Servo(), // Servo 4
    Servo()  // Servo 5
};





// Definition des commandes recu

struct Command {
    int mode;
    int value;
    int id;
};

Command receivedData;
bool commandReceived = false;




void setup() {

    PC_SERIAL.begin(115200);  // USB Serial for PC communication

    while (!PC_SERIAL);       // Wait for serial connection
    PC_SERIAL.println("Starting Setup...");


    // Set Port baudrate to 57600bps. This has to match with DYNAMIXEL baudrate.
    dxl.begin(57600);
    if (dxl.getLastLibErrCode()) {
        PC_SERIAL.println("Could not init serial port!");
        PC_SERIAL.print("Last error code: ");
        PC_SERIAL.println(dxl.getLastLibErrCode());
    }
    // Set Port Protocol Version. This has to match with DYNAMIXEL protocol version.
    if (!dxl.setPortProtocolVersion(DXL_PROTOCOL_VERSION)) {
        PC_SERIAL.println("Could not set protocol version!");
        PC_SERIAL.print("Last error code: ");
        PC_SERIAL.println(dxl.getLastLibErrCode());
    }

    PC_SERIAL.println("Configuring Dynamixel motors...");
    for (int i = 0; i < N_DXL; i++) {

        uint8_t id = DXL_IDs[i];

        if (dxl.ping(id)) {
            dxl.torqueOff(id);
            dxl.setOperatingMode(id, OP_POSITION);
            dxl.torqueOn(id);

            // Limit the maximum velocity in Position Control Mode. Use 0 for Max speed
            dxl.writeControlTableItem(ControlTableItem::PROFILE_VELOCITY, id, 30);

            PC_SERIAL.print("✅ Moteur ID ");
            PC_SERIAL.print(id);
            PC_SERIAL.println(" initialisé !");
        }

        else {
            PC_SERIAL.print("❌ Échec du ping du moteur ID ");
            PC_SERIAL.println(id);
        }
    }

    PC_SERIAL.println("Configuring PWM servos...");

    for (uint8_t i = 0; i < 6; i++) {

        Servos_PWM[i].attach(i);
        PC_SERIAL.print("✅ Moteur ID ");
        PC_SERIAL.print(i);
        PC_SERIAL.println(" initialisé !");
    }
    
    
    PC_SERIAL.println("READY");  // Signale au PC que l'Arduino est prêt

}




void loop() {
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n'); // Lire jusqu'au saut de ligne
        if (sscanf(input.c_str(), "%d,%d,%d", &receivedData.mode, &receivedData.value, &receivedData.id) == 3) {
            commandReceived = true;
        }
    }

    if (commandReceived) {
        //Serial.print("Mode: "); Serial.print(receivedData.mode);
        //Serial.print(" | Value: "); Serial.print(receivedData.value);
        //Serial.print(" | ID: "); Serial.println(receivedData.id);


        switch (receivedData.mode)
        {
        case 0: // Set position dynamixel
            Serial.println("Setting position dynamixel...");
            dxl.setGoalPosition(receivedData.id, receivedData.value);
            dxl.setGoalPosition(receivedData.id, receivedData.value, UNIT_DEGREE);
            break;

        case 1: // Set position PWM
            Serial.println("Setting position PWM...");
            Servos_PWM[receivedData.id].write(receivedData.value);
            break;
        
        default:
        Serial.println("❌ Commande non reconnue !");
            break;
        }

        commandReceived = false;
        
    }

    //PC_SERIAL.println("READY");  // Signale au PC que l'Arduino est prêt

    delay(500);
    //delay(5);
}
