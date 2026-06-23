/*

Spirit Robot:  Infrared (IR) module

Extracted from Hardware.ino (no behavior change). Contains the IR transmit /
receive driver, the IR receive interrupt handler, the IR remote button table,
and the Timer1-based IR carrier modulation.

All function prototypes and shared IR state variables are declared in
Hardware.h, so these definitions are visible to the rest of the sketch exactly
as before. EnableIROutputs() is provided by the Ringo hardware library.

IR transmit/receive functions are based on:
http://playground.arduino.cc/Code/InfraredReceivers by Paul Malmsten
https://github.com/z3t0/Arduino-IRremote by Ken Shirriff

License: Creative Commons Attribution-ShareAlike 2.0 Generic (CC BY-SA 2.0)
Original authors: Dustin Soodak, Kevin King (Plum Geek LLC).

*/

#include "Hardware.h"

byte irData[4]={0x00,0xFF,0x00,0x00};

// ***************************************************
// IR Transmit / Receive
// ***************************************************

void TxIR(unsigned char *Data, int Length){//Ver. 1.2, Dustin Soodak
    int i;
    char j;
    const uint16_t Freq=38000,UsOn=5; //For R2=2k pull up, 8 us delay before pin falls. Inputs (28000,5) give a decent square wave in this case. 
    RxIRStop();
    EnableIROutputs(1);
    ModulateIR(Freq,UsOn);
    delayMicroseconds(9000);
    EnableIROutputs(0);               //EnableIROutputs(0) turns off IR 38khz out but this makes receiver voltage go high.
    delayMicroseconds(4500);
    EnableIROutputs(1);
    delayMicroseconds(520);
    for(i=0;i<Length;i++){      
      for(j=0;j<8;j++){
        EnableIROutputs(0);
        if((Data[i])&(1<<j))
          delayMicroseconds(1610);
        else
          delayMicroseconds(580);
        EnableIROutputs(1);
        delayMicroseconds(520);
      }      
    }//end for(i=0;i<Length;i++)    
    ModulateIR(38000, 0);
    EnableIROutputs(1); 
}//end TxIR()

void TxIRKey(byte key){//Ver. 1.0, Kevin King
  if(key<1){
    // do nothing
  }
  else if(key>21){
    // do nothing
  }
  else{     // actually send IR key if it was within correct range
  key-=1;   //subract 1 from key number so it matches array IRRemoteButtons
  irData[0]=0x00;irData[1]=0xFF;     // all remote keys begin with 0x00, 0xFF
  irData[2]=IRRemoteButtons[key][0]; // add 3rd value
  irData[3]=IRRemoteButtons[key][1]; // add 4th value
  TxIR(irData,4);                    // actually transmit via any enabled IR sources
  }
}//end TxIRKey()

int IRTransitionCount=0;
unsigned char IRBitNum=0,IRByte=0,IRNumOfBytes=0;
unsigned char IRBytes[20];
uint16_t IRPrevTime=0,IRTime;
uint32_t MsAtLastIR=0;//used for end of communication timeout
volatile char IRReceiving=0;
char IRActive=0;
char IRMaxByteCount=4;


void RxIRRestart(char BytesToLookFor){//Ver. 1.2, Dustin Soodak
  detachInterrupt(0);//interrupt 0 is I/O 2 which is _38kHz_R
  TCCR1A = 0x00;          // COM1A1=0, COM1A0=0 => Disconnect Pin OC1 from Timer/Counter 1 -- PWM11=0,PWM10=0 => PWM Operation disabled
  // ICNC1=0 => Capture Noise Canceler disabled -- ICES1=0 => Input Capture Edge Select (not used) -- CTC1=0 => Clear Timer/Counter 1 on Compare/Match
  // CS12=0 CS11=1 CS10=1 => Set prescaler to clock/64
  TCCR1B = 0x03;          // 8MHz clock with prescaler 0x03 means TCNT1 increments every 8uS
  // ICIE1=0 => Timer/Counter 1, Input Capture Interrupt Enable -- OCIE1A=0 => Output Compare A Match Interrupt Enable -- OCIE1B=0 => Output Compare B Match Interrupt Enable
  // TOIE1=0 => Timer 1 Overflow Interrupt Enable
  TIMSK1 = 0x00;          
  pinMode(_38kHz_Rx, INPUT_PULLUP);  
  IRReceiving=0;  
  IRTransitionCount=0;
  IRPrevTime=0;
  MsAtLastIR=0;IRBitNum=0;IRByte=0;IRNumOfBytes=0;
  IRActive=1;
  IRMaxByteCount=BytesToLookFor;
  attachInterrupt(0, IRHandler, CHANGE);//interrupt 0 is I/O 2 which is _38kHz_Rx  
}
void RxIRStop(void){//Ver. 1.2, Dustin Soodak
  detachInterrupt(0);//interrupt 0 is I/O 2 which is _38kHz_Rx    
  TCCR1B=0;//turn off timer        
  pinMode(_38kHz_Rx, INPUT_PULLUP);  
  
  MsAtLastIR=0;//so IRHandler() recognizes it as first falling edge of next transition
  IRReceiving=0;
  IRActive=0;
  IRTransitionCount=0;//so IsIRDone() does not expect anything just because RxIRStop() called.
}

// Infrared transmit and recieve functions are based on:
//http://playground.arduino.cc/Code/InfraredReceivers by Paul Malmsten 
//https://github.com/z3t0/Arduino-IRremote by Ken Shirriff

void IRHandler(void){//Ver. 2.0, Dustin Soodak, Kevin King
  //using interrupt 1 is I/O 3 which is _38kHz_Rx  
  int16_t dTime;
  char Level;
  noInterrupts();
  IRTime=TCNT1;
   
  Level=digitalRead(_38kHz_Rx);  

  if(!Level){//note; 38khz IR signal makes level go low
    IRReceiving=1;
  }
  if((millis()-MsAtLastIR>15) && (IRNumOfBytes<IRMaxByteCount)) {//should never be more than 9 inside valid signal
    TCNT1=0;
    IRPrevTime=0;
    IRTransitionCount=0;
    IRBitNum=0;IRNumOfBytes=0;IRByte=0;  
    //IRReceiving=1;  
  }  
  else{  
    if(IRTime>IRPrevTime)
      dTime=IRTime-IRPrevTime;
    else
      dTime=0xFFFF-IRPrevTime+1+IRTime;   
    IRPrevTime=IRTime;    
    dTime=dTime<<3;
    if(IRTransitionCount>=3 && (IRTransitionCount&1)){//should be high
      if(dTime>1000){
        IRByte|=(1<<IRBitNum); 
      }
      if(dTime<300){//error
         IRNumOfBytes=0;
         IRReceiving=0;
      }
      IRBitNum++;
      if(IRBitNum>7){
        if(IRNumOfBytes<IRMaxByteCount){
          IRBytes[IRNumOfBytes]=IRByte;
          IRNumOfBytes++;
        }        
        else{
           IRReceiving=0;           
        }
        IRBitNum=0; 
        IRByte=0;               
      }      
    }
    IRTransitionCount++;
  }
  MsAtLastIR=millis();
  interrupts();
}

char IsIRDone(void){//Ver. 1.0, Dustin Soodak
  return ((millis()-MsAtLastIR>40 || IRNumOfBytes==IRMaxByteCount) && IRTransitionCount);  
}

//Note: first and second bytes are always 0x00 and 0xFF. IRRemoteButtons[] contains the third and fourth bytes.
const byte IRRemoteButtons[][2]={
  {0x0C,0xF3},//"1" key: 1
  {0x18,0xE7},//"2" key: 2
  {0x5E,0xA1},//"3" key: 3
  {0x08,0xF7},//"4" key: 4
  {0x1C,0xE3},//"5" key: 5
  {0x5A,0xA5},//"6" key: 6
  {0x42,0xBD},//"7" key: 7
  {0x52,0xAD},//"8" key: 8
  {0x4A,0xB5},//"9" key: 9
  {0x16,0xE9},//"0" key: 10
  {0x40,0xBF},//"FORWARD" key: 11
  {0x07,0xF8},//"LEFT" key: 12
  {0x09,0xF6},//"RIGHT" key: 13
  {0x19,0xE6},//"BACKWARD" key: 14
  {0x45,0xBA},//"POWER" key: 15
  {0x46,0xB9},//"PLUM LOGO" key: 16
  {0x47,0xB8},//"MENU" key: 17
  {0x44,0xBB},//"A" key: 18
  {0x43,0xBC},//"B" key: 19
  {0x15,0xEA},//"PLAY" key: 20
  {0x0D,0xF2}//"X" key: 21
};
byte GetIRButton(void){//Ver. 2.0, Dustin Soodak, Kevin King
  byte ButtonNumber=0,i;

    for(i=0;i<sizeof(IRRemoteButtons)/2;i++){
      if(IRBytes[2]==IRRemoteButtons[i][0] && IRBytes[3]==IRRemoteButtons[i][1]){
        ButtonNumber=i+1;
        break; 
      }
    } 

    return ButtonNumber;       //return the button number that was pressed
    
}// end GetIRButton()


// ***************************************************
// IR Data Sending (Timer1 carrier modulation)
// ***************************************************

void ModulateIR(unsigned int Frequency, unsigned int OnTime){//Ver. 1.0, Dustin Soodak 
  //ModulateIR(38000,6) seems to produce best square wave for 38kHz.
  //Frequency is in Hz
  //OnTime is in units of UsOn
  uint16_t period,dutycycle;
  uint8_t prescalerbits;
  if(OnTime>100)
    OnTime=100;
  if (F_CPU/Frequency/2>=0x10000){
    if(F_CPU/Frequency/2>=0x10000*8){
        prescalerbits=0b011;//prescaler 64
        period=F_CPU/Frequency/(2*16);
        dutycycle=F_CPU/1000000*OnTime/2/64;               
    }
    else{
      prescalerbits = 0b010;// prescaler 8
      period=F_CPU/Frequency/(2*8);
      dutycycle=F_CPU/1000000*OnTime/2/8;
    }
  }
  else{
    prescalerbits = 0b001;  //on but no prescaling
    period=F_CPU/Frequency/(2*1);
    dutycycle=F_CPU/1000000*OnTime/2/1;
  }
  if(OnTime==0){
    TCCR1A=0;
    TCCR1B=0;
   // pinMode(Chirp,INPUT);
    
    //Serial.println("off");
  }
  else{
    TCCR1B&=~0b00000111;//turn off timer    
    ICR1=period;
    OCR1B=dutycycle;
    TCCR1A = (0b10<<4) | 0b10;//COM1B1 COM1B0, and WGM11 WGM10
    TCCR1B = (0b10<<3) | prescalerbits;//WGM13 WGM12, and off/(on with prescaler)    
  }
}

void PlayChirpIR(unsigned int Frequency, unsigned int OnTime){//Ver. 1.0, Dustin Soodak
  // ModulateIR used to be called PlayChirpIR, left in for backward compatibility.
   ModulateIR(Frequency,OnTime); 
}

char CheckMenuButton(void){
  byte button;
  if(IsIRDone()){              //wait for an IR remote control command to be received
      button = GetIRButton();  // read which button was pressed, store in "button" variable
      RxIRRestart(4);          // restart looking for another buttom press
      if(button == 17){         // button 17 is the "MENU" button on the IR remote
      return 1;
      }
      else{
      return 0;  
      }
  }
  return 0;
}

// ***************************************************
// end IR
// ***************************************************
