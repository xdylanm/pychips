#ifndef _ADC120_h
#define _ADC120_h

int ADC120_init();
float ADC120_read(int ch, unsigned baud);
int ADC120_readn(int num_ch, int* ch, float* raw_val, unsigned baud);

#endif
