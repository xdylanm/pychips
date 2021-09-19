Build lines

gcc -Wall -o ../build/test_ADC120 -I../ -lpigpiod_if2 -lrt -L/home/pi/Source/pychips/ADC120/build/ -lADC120 test_ADC120.c
