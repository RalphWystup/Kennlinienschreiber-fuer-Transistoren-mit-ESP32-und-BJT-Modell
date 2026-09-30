// ---------------- ad_da ----------------------------------------

#include <Wire.h>
#include <SPI.h>
#include "modbus.h"
#include "ad_da.h"

SPISettings SPISettings_AD7682(400000, MSBFIRST, SPI_MODE0);
SPISettings SPISettings_DAC8565(400000, MSBFIRST, SPI_MODE2);

uint16_t getAD7682(int aCS, uint8_t aKanal, uint16_t aRange){
  uint8_t c[2];
  digitalWrite(aCS, LOW);
  delayMicroseconds(1);
  aRange |= (aKanal << 9); // << (7+2)
  c[0]=highByte(aRange);
  c[1]=lowByte(aRange);
  SPI.transfer(c, 2);
  delayMicroseconds(1);
  digitalWrite(aCS, HIGH);
  delayMicroseconds(1);
  return (c[0]<<8) | c[1];
} // getAD7682

uint16_t calc_miw(uint16_t mw, uint16_t *miws, int *imiw, int NMIW){
  miws[*imiw]=mw; 
  (*imiw)++;
  if (*imiw>=NMIW) *imiw=0;
  int miw_sum=miws[0];
  for (int n=1; n<NMIW; n++) miw_sum+=miws[n];
  return miw_sum / NMIW;
} // calc_miw

void ReadADCs(){
#define AD_MODE (0x2000 | 0x1C00 | 0x0008 | 0x0001) << 2 // CFG update | Unipol to GND | low BW, int 4,096V | no SEQ, no read CFG
  SPI.beginTransaction(SPISettings_AD7682); 
  static uint16_t miws0[NMIW_AD]={}, miws1[NMIW_AD]={}, miws2[NMIW_AD]={}, miws3[NMIW_AD]={};
  static int imiw0=0,imiw1=0,imiw2=0,imiw3=0;
  // bei der Abfrage wird Kanal+1 angefragt und Kanal-1 geliefert:
  reg[REG_AD0+0]=getAD7682(PIN_CS_AD,2, AD_MODE); // cs2, CH0=Urc1, sigle 0..4V
  reg[REG_ADMIW+0]=calc_miw(reg[REG_AD0+0], miws0,&imiw0, NMIW_AD);

  reg[REG_AD0+1]=getAD7682(PIN_CS_AD,3, AD_MODE); // cs2, CH1=Urc2, sigle 0..4V
  reg[REG_ADMIW+1]=calc_miw(reg[REG_AD0+1], miws1,&imiw1, NMIW_AD);

  reg[REG_AD0+2]=getAD7682(PIN_CS_AD,0, AD_MODE); // cs2, CH2=Urb1, sigle 0..4V
  reg[REG_ADMIW+2]=calc_miw(reg[REG_AD0+2], miws2,&imiw2, NMIW_AD);

  reg[REG_AD0+3]=getAD7682(PIN_CS_AD,1, AD_MODE); // cs2, CH3=Urb2, sigle 0..4V
  reg[REG_ADMIW+3]=calc_miw(reg[REG_AD0+3], miws3,&imiw3, NMIW_AD);

  SPI.endTransaction();
} // ReadADCs

void setDAC8565(int aCS, int aKanal, uint16_t aWert){ // 4x DA 0..2.5V
  uint8_t c[3];
  digitalWrite(aCS, LOW);
  delayMicroseconds(1);
  c[0]=(aKanal << 1) | 0x10;
  c[1]=highByte(aWert);
  c[2]=lowByte(aWert);
  SPI.transfer(c, 3);
  delayMicroseconds(1);
  digitalWrite(aCS, HIGH);
  delayMicroseconds(1);
} // setDAC8565

void WriteDAs(){
  SPI.beginTransaction(SPISettings_DAC8565); 
  setDAC8565(PIN_CS_DA, 0,reg[REG_DA0+0]); // UC
  setDAC8565(PIN_CS_DA, 1,reg[REG_DA0+1]); // UB
  // ch2, ch3: NC
  SPI.endTransaction();
} // WriteDAs



void setup_ad_da(){
  SPI.begin();
  pinMode(PIN_CS_AD, OUTPUT);
  pinMode(PIN_CS_DA, OUTPUT);
  digitalWrite(PIN_CS_AD, HIGH);
  digitalWrite(PIN_CS_DA, HIGH);
} // setup_ad_da


void WorkAdDa(){
  ReadADCs();
  WriteDAs();
} // WorkAdDa
