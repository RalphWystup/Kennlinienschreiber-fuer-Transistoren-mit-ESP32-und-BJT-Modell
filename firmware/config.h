// ---------------- config ----------------------------------------

#ifndef __CONFIG_H__
#define __CONFIG_H__
#include <Arduino.h>

#define SerialUSB Serial
#define MODBUS_ADR 1

#define PIN_CS_DA  5
#define PIN_CS_AD 17
#define PIN_MB_LED 22

#define REG_DA0          0  // 4 Register, Uc, Ub, NC,NC
#define REG_AD0          4  // 4 Register, Urc1, Urc2, Urb1, Urb2
#define REG_ADMIW        8  // 4 Register, wie REG_AD0 als Mittelwerte
#define MAX_REG         13  // 12=letzter Register

#define NMIW_AD   10 // Anzahl für Mittelwert

#endif /* ifndef */