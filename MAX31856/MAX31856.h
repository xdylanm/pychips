#ifndef _MAX31856_h
#define _MAX31856_h

int MAX31856_init();
float MAX31856_read(int ch, unsigned baud);
int MAX31856_readn(int num_ch, int* ch, float* raw_val, unsigned baud);

#endif

