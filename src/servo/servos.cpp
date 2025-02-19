#include "servos.h"


// Create an array of Servo objects
Servo servos[MAX_SERVOS];

/**
 * @brief Attach the servos to their designated pins and set initial positions.
 */
void initMarcusControl() {
  servos[0].attach(SERVO_PAN_PIN);      // Pan servo
  servos[1].attach(SERVO_TILT_PIN);     // Tilt servo
  servos[2].attach(SERVO_JAW_PIN);      // Jaw servo
  servos[3].attach(SERVO_EMOTION_PIN);  // Emotion servo

  // Initialize servos to default/neutral positions
  servos[0].write(90);   // Center for pan
  servos[1].write(90);   // Center for tilt
  servos[2].write(0);    // Jaw closed (adjust as needed)
  servos[3].write(90);   // Neutral position for emotion
}

/**
 * @brief Update servo positions based on the command type.
 *
 * For COMMAND_MOVETO, the x and y values are mapped to pan and tilt angles.
 * For COMMAND_TALK, a simple jaw movement is executed.
 * For COMMAND_MIRROR_EMOTION, the emotion string determines the servo position.
 *
 * @param cmd The command to execute.
 */
void executeMarcusCommand(MarcusCommand cmd) {
  switch(cmd.command) {
    case COMMAND_MOVETO:
      {
        // Map x and y values to servo angles.
        // Here, we assume the input range is [0, 1023] mapping to [0, 180] degrees.
        int panAngle = map(cmd.x, 0, 1023, 0, 180);
        int tiltAngle = map(cmd.y, 0, 1023, 0, 180);
        servos[0].write(panAngle);
        servos[1].write(tiltAngle);
      }
      break;

    case COMMAND_TALK:
      {
        // For the TALK command, animate the jaw servo.
        // This example simply opens and closes the jaw.
        servos[2].write(30);    // Open jaw (adjust angle as needed)
        delay(100);             // Short pause for effect
        servos[2].write(0);     // Close jaw
      }
      break;

    case COMMAND_MIRROR_EMOTION:
      {
        // Adjust the emotion servo based on the received emotion.
        if (strcmp(cmd.emotion, "anger") == 0) {
          servos[3].write(45);    // Example angle for "anger"
        } else if (strcmp(cmd.emotion, "happy") == 0) {
          servos[3].write(135);   // Example angle for "happy"
        } else {
          // Default to neutral position
          servos[3].write(90);
        }
      }
      break;

    case COMMAND_IDLE:
    default:
      // For idle or unrecognized commands, no action is taken.
      break;
  }
}

/**
 * @brief Parse the incoming JSON message and extract command parameters.
 *
 * This function uses ArduinoJson to parse the message, populates a MarcusCommand
 * structure, and then calls executeMarcusCommand() to perform the action.
 *
 * @param message The incoming JSON message as a C-string.
 */
void processMarcusMessage(const char* message) {
  // Estimate a JSON document capacity (adjust if your messages become more complex)
  const size_t capacity = 256;
  DynamicJsonDocument doc(capacity);

  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.f_str());
    return;
  }

  // Get the "payload" object from the message
  JsonObject payload = doc["payload"];
  if (!payload) {
    Serial.println("No payload found in the message.");
    return;
  }

  // Initialize our command structure
  MarcusCommand cmd;
  memset(&cmd, 0, sizeof(cmd));  // Zero the memory for safety

  const char* commandStr = payload["command"];
  if (!commandStr) {
    Serial.println("No command specified in payload.");
    return;
  }
  
  // Determine the command type and extract parameters accordingly.
  if (strcmp(commandStr, "MOVETO") == 0) {
    cmd.command = COMMAND_MOVETO;
    cmd.x = payload["x"] | 0;   // Default to 0 if not found
    cmd.y = payload["y"] | 0;
  } else if (strcmp(commandStr, "TALK") == 0) {
    cmd.command = COMMAND_TALK;
    const char* text = payload["text"];
    if (text) {
      strncpy(cmd.text, text, sizeof(cmd.text) - 1);
    }
  } else if (strcmp(commandStr, "MIRROR EMOTION") == 0) {
    cmd.command = COMMAND_MIRROR_EMOTION;
    const char* emotion = payload["emotion"];
    if (emotion) {
      strncpy(cmd.emotion, emotion, sizeof(cmd.emotion) - 1);
    }
  } else {
    cmd.command = COMMAND_IDLE;
  }

  // Execute the command based on the populated structure.
  executeMarcusCommand(cmd);
}
