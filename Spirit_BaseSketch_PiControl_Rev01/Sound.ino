/*

Spirit Robot:  Sound / Animation module

Extracted from Hardware.ino (no behavior change). Contains the short canned
chirp/eye animations and the playSweep() tone helper. These call playChirp()/
offChirp() (Comms.ino), the pixel/eye helpers (Pixels.ino), and the NOTE_*
constants, all of which are declared in the project headers.

License: Creative Commons Attribution-ShareAlike 2.0 Generic (CC BY-SA 2.0)
Original authors: Dustin Soodak, Kevin King (Plum Geek LLC).

*/

#include "Hardware.h"

// ***************************************************
// Short Animations
// ***************************************************

void playStartChirp(void){//Ver. 1.0, Kevin King   
  // This is the startup sequence that plays when Ringo is reset(put in begin())
  playChirp(1000);
  onEyes(40,0,50);  // blue
  delay(50);
  playChirp(2000);
  delay(50);
  playChirp(3000);
  delay(50);
  playChirp(4000);
  delay(100);
  offChirp();
  offEyes();
}

void playQuickChirp(void){//Ver. 1.0, Kevin King   
  // This is the startup sequence that plays when Ringo is reset(put in begin())
  playChirp(2000);
  onEyes(40,0,50);  // blue
  delay(30);
  offChirp();
  offEyes();
}

void playAck(void){//Ver. 1.0, Kevin King
  playChirp(NOTE_C7);
  setPixelRGB(BODY_TOP,0,30,0);//RefreshPixels();
  delay(50);
  offChirp();
  setPixelRGB(BODY_TOP,0,0,0);//RefreshPixels();
}


void playNonAck(void){//Ver. 1.0, Kevin King
  playChirp(NOTE_CS6);
  setPixelRGB(BODY_TOP,30,0,0);//RefreshPixels();
  delay(75);
  offChirp();
  setPixelRGB(BODY_TOP,0,0,0);//RefreshPixels();
}


void playAnger(void){//Ver. 1.0, Dustin Soodak
  char i;
  for(i=0;i<6;i++){
    playChirp(NOTE_C6);
    delay(20);
    playChirp(NOTE_CS6);   
    delay(20);  
  }
  offChirp();  
}


void playBoredom(void){//Ver. 1.0, Dustin Soodak
  char i;
  unsigned int dfreq;
  dfreq=(NOTE_DS6-NOTE_C6)>>4;
  playChirp(NOTE_C6);
  delay(50);
  for(i=0;i<16;i++){    
    playChirp(NOTE_C6+dfreq*i);
    delay(10);
  }
  playChirp(NOTE_DS6);
  delay(100);
    for(i=0;i<16;i++){    
    playChirp(NOTE_DS6-dfreq*i);
    delay(10);
  }
  playChirp(NOTE_C6);
  delay(50);
  offChirp();
}


void playExcited(void){//Ver. 1.0, Dustin Soodak, Kevin King (note sequence)
  playChirp(NOTE_G6);
  delay(100);
  playChirp(NOTE_C7);
  delay(100);
  playChirp(NOTE_A6);
  delay(100);
  playChirp(NOTE_C7);
  delay(100);
  playChirp(NOTE_B6);
  delay(100);  
  playChirp(NOTE_G6);
  delay(100);
  offChirp();
}

// ***************************************************
// end Short Animations
// ***************************************************


// ***************************************************
// Chirp tone helper
// ***************************************************

void playSweep(int StartNote, int EndNote, int DwellTime){//Ver. 1.0, Kevin King
  if(StartNote<EndNote){
      for(; StartNote<=EndNote; StartNote++){
      playChirp(StartNote);
      delayMicroseconds(DwellTime);
     }
  }
   else{
     for(; StartNote>=EndNote; StartNote--){
      playChirp(StartNote);
      delayMicroseconds(DwellTime);
     }  
  }
 offChirp(); 
}

// ***************************************************
// end Chirp tone helper
// ***************************************************
