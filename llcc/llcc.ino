#include <Arduino.h>

// 电机控制引脚配置，对于每个电机，按照{EN, STEP, DIR}的顺序
const int motorPins[8][3] = {
  {1, 2, 3},    // 电机 1
  {4, 5, 6},    // 电机 2
  {7, 8, 9},    // 电机 3
  {10, 11, 12}, // 电机 4
  {13, 14, 15}, // 电机 5
  {16, 17, 18}, // 电机 6
  {19, 20, 21}, // 电机 7
  {22, 23, 24}  // 电机 8
};

// 步进电机的步进角度
const float stepAngle = 1.8;

// 用于存储电机命令的结构体
struct MotorCommand {
  int motorNumber;        // 电机编号
  bool direction;         // 旋转方向
  unsigned long steps;    // 已执行的步数
  unsigned long lastStepTime; // 上一步的执行时间
  unsigned long stepInterval; // 步进间隔时间，用于控制速度
  unsigned long totalSteps;   // 总共需要执行的步数
};

MotorCommand commands[8]; // 存储每个电机的命令
int activeMotors = 0;     // 当前活跃的电机数量

void setup() {
  Serial.begin(19200); // 初始化串口通信
  
  // 初始化电机控制引脚为输出模式，并确保电机启用（EN引脚为低电平）
  for (int i = 0; i < 8; i++) {
    for (int j = 0; j < 3; j++) {
      pinMode(motorPins[i][j], OUTPUT);
      digitalWrite(motorPins[i][0], LOW);
    }
  }
}

void loop() {
  if (Serial.available() > 0) {
    // 读取串口接收到的命令
    String commandLine = Serial.readStringUntil('\n');
    Serial.println(commandLine); // 回显接收到的命令
    activeMotors = 0; // 重置活跃电机计数

    // 解析接收到的命令行为单个电机的命令
    int cmdStart = 0;
    for (int i = 0; i <= commandLine.length(); i++) {
      if (i == commandLine.length() || commandLine.charAt(i) == '/') {
        String command = commandLine.substring(cmdStart, i);
        if (command.length() > 1) {
          // 从命令中提取电机编号、方向、旋转角度和速度
          int motorNumber = command.charAt(0) - '0' - 1;
          bool direction = command.charAt(1) == '+' ? HIGH : LOW;
          int speed = command.substring(command.indexOf(',', 2) + 1).toInt();
          int degrees = command.substring(2, command.indexOf(',', 2)).toInt();
          unsigned long steps = abs(degrees) / stepAngle;

          // 为这个电机设置命令
          digitalWrite(motorPins[motorNumber][2], direction); // 设置方向
          commands[motorNumber].motorNumber = motorNumber;
          commands[motorNumber].direction = direction;
          commands[motorNumber].stepInterval = 1000000 / speed; // 将速度转换为步进间隔时间（微秒）
          commands[motorNumber].lastStepTime = micros();
          commands[motorNumber].totalSteps = steps;
          commands[motorNumber].steps = 0;
          activeMotors++; // 增加活跃电机计数
        }
        cmdStart = i + 1;
      }
    }
  }

  // 根据解析的命令执行每个电机的步进操作
  for (int i = 0; i < 8; i++) {
    if (commands[i].totalSteps > commands[i].steps) {
      unsigned long currentTime = micros();
      if (currentTime - commands[i].lastStepTime >= commands[i].stepInterval) {
        // 执行步进
        digitalWrite(motorPins[i][1], HIGH);
        delayMicroseconds(10); // 确保步进信号被电机驱动器识别
        digitalWrite(motorPins[i][1], LOW);
        
        commands[i].steps++;
        commands[i].lastStepTime = currentTime;

        // 如果电机已完成指定的步数
        if (commands[i].steps >= commands[i].totalSteps) {
          activeMotors--; // 减少活跃电机计数
        }
      }
    }
  }


}
