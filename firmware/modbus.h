// ---------------- modbus ----------------------------------------

#ifndef __MODBUS_H__
#define __MODBUS_H__
#include "config.h"

extern "C"{

extern uint16_t reg[MAX_REG];

void setup_modbus();
void WorkModbus();

} // extern "C"
#endif /* ifndef */