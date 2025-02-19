#ifndef MARCUS_H
#define MARCUS_H

#include <Arduino.h>
#include <ArduinoJson.h>

// Maximum number of servos (adjust according to your hardware setup)
#define MAX_SERVOS 4

// Servo pin assignments (adjust these to your wiring)
#define SERVO_PAN_PIN      3   // For horizontal (pan) movement
#define SERVO_TILT_PIN     4   // For vertical (tilt) movement
#define SERVO_JAW_PIN      5   // For jaw (talk) movement
#define SERVO_EMOTION_PIN  6   // For mirroring emotion

// Enumeration for command types
enum MarcusCommandType {
  COMMAND_IDLE,
  COMMAND_TALK,
  COMMAND_MOVETO,
  COMMAND_MIRROR_EMOTION
};

// Internal representation for a command received from the central computer.
typedef struct {
  MarcusCommandType command;  // Command type
  int x;                      // For LOOKAT command: x-coordinate
  int y;                      // For LOOKAT command: y-coordinate
  char emotion[16];           // For MIRROR EMOTION command: emotion string
  char text[64];              // For TALK command: optional text
} MarcusCommand;

// Function prototypes

/**
 * @brief Initialize the servo motors and any related hardware.
 */
void initMarcusControl();

/**
 * @brief Execute a MarcusCommand by updating servo positions.
 *
 * @param cmd The MarcusCommand to execute.
 */
void executeMarcusCommand(MarcusCommand cmd);

/**
 * @brief Parse an incoming JSON command message and execute the corresponding command.
 *
 * The expected JSON message format is:
 * {
 *   "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
 *   "source": "central",
 *   "type": "command",
 *   "payload": {
 *     "command": "TALK" | "LOOKAT" | "MIRROR EMOTION",
 *     // For LOOKAT:
 *     "x": 350,
 *     "y": 200,
 *     // For TALK:
 *     "text": "Hello, how can I help you?",
 *     // For MIRROR EMOTION:
 *     "emotion": "anger"
 *   }
 * }
 *
 * @param message The incoming JSON message as a C-string.
 */
void processMarcusMessage(const char* message);

#endif // MARCUS_H
