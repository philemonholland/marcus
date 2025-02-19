#include <Arduino.h>
#include <Dynamixel2Arduino.h>
#include <Servo.h>
#include <stdio.h>
#include <string.h>

#define PROTOCOL_VERSION 2.0
#define DXL_MIN_ANGLE 0
#define DXL_MAX_ANGLE 4095
#define DXL_MOVING_STATUS_THRESHOLD 20

class Motor {
public:
    virtual void set_angle_degrees(float degrees) = 0;
    virtual int get_angle() = 0;
};

class ServoMotor : public Motor {
public:
    ServoMotor(const char* name, int pin) : name(name), pin(pin), initial_angle(0), angle(0) {
        servo.attach(pin);
        set_angle_degrees(initial_angle);
    }
    void set_angle_degrees(float degrees) override {
        angle = constrain(degrees, 0, 180);
        servo.write(map(angle, 0, 180, 0, 180));
    }
    int get_angle() override {
        return angle;
    }
private:
    const char* name;
    int pin;
    float initial_angle;
    float angle;
    Servo servo;
};

class DynamixelMotor : public Motor {
public:
    DynamixelMotor(const char* name, uint8_t id, uint8_t dir_pin, uint8_t baudrate) 
        : name(name), id(id), initial_angle(2048), angle(2048), driver(Serial1, dir_pin) {
        driver.begin(baudrate);
        set_angle_degrees(initial_angle);
    }
    void set_angle_degrees(float degrees) override {
        int new_angle = map(degrees, 0, 360, DXL_MIN_ANGLE, DXL_MAX_ANGLE);
        set_angle(new_angle);
    }
    int get_angle() override {
        return driver.readControlTableItem(ControlTableItem::PRESENT_POSITION, id);
    }
private:
    void set_angle(int new_angle) {
        angle = constrain(new_angle, DXL_MIN_ANGLE, DXL_MAX_ANGLE);
        driver.writeControlTableItem(ControlTableItem::GOAL_POSITION, id, angle);
    }
    const char* name;
    uint8_t id;
    int initial_angle;
    int angle;
    Dynamixel2Arduino driver;
};

class MotorController {
public:
    void add_motor(Motor* motor, const char* name) {
        if (motor_count < MAX_MOTORS) {
            motors[motor_count].motor = motor;
            motors[motor_count].name = name;
            motor_count++;
        }
    }

    void set_motor(const char* name, float degrees) {
        Motor* motor = find_motor(name);
        if (motor) {
            motor->set_angle_degrees(degrees);
        }
    }

    int get_motor(const char* name) {
        Motor* motor = find_motor(name);
        return motor ? motor->get_angle() : -1;
    }
    
    void reset_all() {
        for (int i = 0; i < motor_count; i++) {
            motors[i].motor->set_angle_degrees(0);
        }
    }

private:
    static constexpr int MAX_MOTORS = 10;
    struct MotorEntry {
        const char* name;
        Motor* motor;
    } motors[MAX_MOTORS];
    int motor_count = 0;
    
    Motor* find_motor(const char* name) {
        for (int i = 0; i < motor_count; i++) {
            if (strcmp(motors[i].name, name) == 0) {
                return motors[i].motor;
            }
        }
        return nullptr;
    }
};

ServoMotor xServo("xServo", 2);
ServoMotor yServo("yServo", 3);
DynamixelMotor xDyn("xDyn", 1, 2, 57600);
DynamixelMotor yDyn("yDyn", 2, 2, 57600);
MotorController controller;

void setup() {
    controller.add_motor(&xServo, "xServo");
    controller.add_motor(&yServo, "yServo");
    controller.add_motor(&xDyn, "xDyn");
    controller.add_motor(&yDyn, "yDyn");
}

void loop() {
    if(controller.get_motor("xServo") == 0 && controller.get_motor("yServo") == 0) {
        controller.set_motor("xServo", 180);
        controller.set_motor("yServo", 180);
    } 
    else if(controller.get_motor("xServo") == 180 && controller.get_motor("yServo") == 180) {
        controller.set_motor("xServo", 0);
        controller.set_motor("yServo", 0);
    }
}
