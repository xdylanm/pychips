#include "MAX31856.h"


int MAX31856_init();
float MAX31856_read(int ch, unsigned baud);
int MAX31856_readn(int num_ch, int* ch, float* raw_val, unsigned baud);
