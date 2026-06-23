/*

Spirit Robot:  Pixels module

Extracted from Hardware.ino (no behavior change). Contains all NeoPixel /
eye / wing control. Function prototypes and the shared `pixels` object are
declared in Hardware.h, so these definitions are visible to the rest of the
sketch exactly as before.

These functions use the Adafruit NeoPixel library:
https://github.com/adafruit/Adafruit_NeoPixel

License: Creative Commons Attribution-ShareAlike 2.0 Generic (CC BY-SA 2.0)
Original authors: Dustin Soodak, Kevin King (Plum Geek LLC).

*/

#include "Hardware.h"
#include <Adafruit_NeoPixel.h>

// ***************************************************
// Pixels
// ***************************************************

Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUM_PIXELS, Pixel_Bus, NEO_GRB + NEO_KHZ800);
void setPixelRGB(int Pixel, int Red, int Green, int Blue){//Ver. 1.0, Dustin Soodak
  if(Pixel>NUM_PIXELS)
    Pixel=NUM_PIXELS;
  if(Pixel<0)
    Pixel=0;
  pixels.setPixelColor(Pixel, pixels.Color(Red,Green,Blue));
  pixels.show();//Remove this line and use RefreshPixels() below 
  //              if you want to set several at once for high-speed patterns.
}
void setAllPixelsRGB(int Red, int Green, int Blue){//Ver. 1.1, Dustin Soodak
  char i;
  for(i=0;i<NUM_PIXELS;i++){
    pixels.setPixelColor(i, pixels.Color(Red,Green,Blue)); 
  }
  pixels.show();//added Ver.1.1
}
void RefreshPixels(void){//Ver. 1.0, Dustin Soodak
  pixels.show();  
}

void eyesOff(void){                           //turns eyes off
  setPixelRGB(1,0,0,0);                       //turn off left eye
  setPixelRGB(2,0,0,0);                       //turn off right eye
}

void eyesOn(int red, int green, int blue){    //turns both eyes on same color
  setPixelRGB(1,red,green,blue);              //left eye
  setPixelRGB(2,red,green,blue);              //right eye
}

void leftEye(int red, int green, int blue){
  setPixelRGB(1,red,green,blue);              //control left eye
}

void rightEye(int red, int green, int blue){
  setPixelRGB(2,red,green,blue);              //control right eye
}

void leftWing(int red, int green, int blue){  //set entire wing to the same color
  for (char i=3; i<15; i++){
    setPixelRGB(i,red,green,blue);
  }
}

void rightWing(int red, int green, int blue){ //set entire wing to same color
  for (char i=15; i<27; i++){
    setPixelRGB(i,red,green,blue);
  }
}

void offPixels(void){//Ver. 1.0, Kevin King              //turns off all pixels
  setAllPixelsRGB(0,0,0);                                //set all pixels to off
}

void offPixel(byte Pixel){//Ver. 1.0, Kevin King         //turns off a specific pixel
  setPixelRGB(Pixel,0,0,0);                              //set this pixel to off
}

void onEyes(byte Red, byte Green, byte Blue){//Ver. 1.0, Kevin King     //makes eyes the given color, automatically calls RefreshPixels()
  setPixelRGB(EYE_RIGHT,Red,Green,Blue);                 //set right eye
  setPixelRGB(EYE_LEFT,Red,Green,Blue);                  //set left eye
}

void leftEye(byte Red, byte Green, byte Blue){//Ver. 1.0, Kevin King     //makes left eye the given color, automatically calls RefreshPixels()
  setPixelRGB(EYE_LEFT,Red,Green,Blue);                  //set left eye
}

void rightEye(byte Red, byte Green, byte Blue){//Ver. 1.0, Kevin King     //makes right eye the given color, automatically calls RefreshPixels()
  setPixelRGB(EYE_RIGHT,Red,Green,Blue);                 //set right eye
}

void offEyes(void){//Ver. 1.0, Kevin King                //turns off eye pixels
  setPixelRGB(EYE_RIGHT,0,0,0);                          //blank right eye
  setPixelRGB(EYE_LEFT,0,0,0);                           //blank left eye
}

void randomEyes(void){//Ver. 1.0, Kevin King             //Sets the pair of eyes to a random color
  int red, green, blue;
  red = random(120);
  green = random(120);
  blue = random(120);
  onEyes(red,green,blue);
}

// ***************************************************
// end Pixels
// ***************************************************
