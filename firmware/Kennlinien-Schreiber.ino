#include <Arduino.h>
#include "config.h"
#include "modbus.h"
#include "ad_da.h"

void setup() {
  setup_modbus();
  setup_ad_da();
} // setup

void loop() {
  WorkModbus();
  WorkAdDa();
} // loop
