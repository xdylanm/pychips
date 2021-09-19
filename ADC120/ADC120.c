#include "ADC120.h"
#include "pigpiod_if2.h"
#include <stdio.h>
#include <time.h>

#define ADC120_CS_PIN 21
#define MAX_N_BYTE_XFER 64

int ADC120_init()
{
    // connect to daemon over socket
    int pi = pigpio_start(0,0);
    if (pi < 0) {
        fprintf(stderr, "Failed to connect to pigpiod (%d)\n", pi);
        return -1;
    } 
    
    // set CS pin to pull-up, write 1 and disable
    if (set_pull_up_down(pi, ADC120_CS_PIN, PI_PUD_UP) != 0) {
        fprintf(stderr,"Failed to set pull up on GPIO21.\n");
        pigpio_stop(pi);
        return 1;
    }
   
    if (set_mode(pi, ADC120_CS_PIN, PI_OUTPUT) != 0) { 
        fprintf(stderr, "Failed to set GPIO21 to output.\n");
        pigpio_stop(pi);
        return 1;
    }
 
    gpio_write(pi, ADC120_CS_PIN, 1); // initialize high

    // disconnect
    pigpio_stop(pi);

    return 0;
}

float ADC120_read(int ch, unsigned baud /*=1000000*/)
{
    if (ch < 0 || ch > 7) {
        fprintf(stderr, "Invalid channel (%d).\n",ch);
        return -2;
    } 
        
    // connect to daemon over socket
    int pi = pigpio_start(0,0);
    if (pi < 0) {
        fprintf(stderr, "Failed to connect to pigpiod (%d)\n", pi);
        return -1;
    } 

    // mm     - mode (pol, phase). ADC120 is 11: clock idles high
    // ppp    - 0 if corresponding CS (CS2, CS1, CS0) is active low (default), 1=high
    // uuu    - 0 if corresponding CS (CS2, CS1, CS0) is reserved for SPI, 1 otherwise
    //          Here, were using a software CS, so reserve none
    // A      - 0 for main SPI, 1 for aux (0)
    // W      - 0 if not 3 wire, 1 if 3 wire (shared MOSI/MISO) (0)
    // nnnn   - ignored for W=0
    // T      - aux SPI only
    // R      - aux SPI only
    // bbbbbb - aux SPI only
    //                            3       2       1       0
    //                               bbbbbbRTnnnnWAuuupppmm
    unsigned const spi_flags = 0b00000000000000000000000011100011;

    int spi = spi_open(pi, 0, baud, spi_flags);
    if (spi < 0) {
        fprintf(stderr, "Failed to open SPI bus (%d)\n", spi);
        return -1;
    } 
    
    char tx_buf[2];
    tx_buf[0] = 0x3C & (ch << 3);
    tx_buf[1] = 0;
    char rx_buf[2];
    rx_buf[0] = 0;
    rx_buf[1] = 0;
    
    // CS low to start transfer
    gpio_write(spi, ADC120_CS_PIN, 0);

    int xfer_count = spi_xfer(pi, spi, &tx_buf[0], &rx_buf[0], 2);
    
    // CS high to end transfer
    gpio_write(spi, ADC120_CS_PIN, 1); 
    
    if (xfer_count != 2) {
        fprintf(stderr, "SPI transfer failed (%d).\n", xfer_count);
        rx_buf[0] = 0;
        rx_buf[1] = 0;
    }
    
    float const read_out = (((unsigned)(rx_buf[0] & 0x0F) << 8) + rx_buf[1])/4095.0;

    // disconnect
    spi_close(pi, spi);
    pigpio_stop(pi);

    return read_out;    

}

int ADC120_readn(int num_ch, int* ch, float* raw_val, unsigned baud /*=1000000*/)
{
    char tx_buf[MAX_N_BYTE_XFER];
    char rx_buf[MAX_N_BYTE_XFER];
    if (num_ch > MAX_N_BYTE_XFER/2) {
        fprintf(stderr, "Maximum sequential reads is limited to %d.", MAX_N_BYTE_XFER/2);
        return -3;
    }

    for (int i = 0; i < num_ch; ++i) {
        if (ch[i] < 0 || ch[i] > 7) {
            fprintf(stderr, "Invalid channel (%d:%d).\n",i,ch[i]);
            return -2;
        } 
    }
        
    // connect to daemon over socket
    int pi = pigpio_start(0,0);
    if (pi < 0) {
        fprintf(stderr, "Failed to connect to pigpiod (%d)\n", pi);
        return -1;
    } 

    // mm     - mode (pol, phase). ADC120 is 11: clock idles high
    // ppp    - 0 if corresponding CS (CS2, CS1, CS0) is active low (default), 1=high
    // uuu    - 0 if corresponding CS (CS2, CS1, CS0) is reserved for SPI, 1 otherwise
    //          Here, were using a software CS, so reserve none
    // A      - 0 for main SPI, 1 for aux (0)
    // W      - 0 if not 3 wire, 1 if 3 wire (shared MOSI/MISO) (0)
    // nnnn   - ignored for W=0
    // T      - aux SPI only
    // R      - aux SPI only
    // bbbbbb - aux SPI only
    //                            3       2       1       0
    //                               bbbbbbRTnnnnWAuuupppmm
    unsigned const spi_flags = 0b00000000000000000000000011100011;

    int spi = spi_open(pi, 0, baud, spi_flags);
    if (spi < 0) {
        fprintf(stderr, "Failed to open SPI bus (%d)\n", spi);
        return -1;
    } 

    for (int i = 0; i < num_ch; ++i) {
        tx_buf[2*i] = 0x3C & (ch[i] << 3);
        tx_buf[2*i+1] = 0;
        rx_buf[2*i] = 0;
        rx_buf[2*i+1] = 0;
    }
    
    // CS low to start transfer
    gpio_write(spi, ADC120_CS_PIN, 0);

    int xfer_count = spi_xfer(pi, spi, &tx_buf[0], &rx_buf[0], 2*num_ch);
    
    // CS high to end transfer
    gpio_write(spi, ADC120_CS_PIN, 1); 
    
    if (xfer_count != 2*num_ch) {
        fprintf(stderr, "SPI transfer failed (%d).\n", xfer_count);
        for (int i = 0; i < 2*num_ch; ++i) {
            rx_buf[i] = 0;
        }
    }
   
    for (int i = 0; i < num_ch; ++i) { 
        raw_val[i] = (((unsigned)(rx_buf[2*i] & 0x0F) << 8) + rx_buf[2*i+1])/4095.0;
    }

    // disconnect
    spi_close(pi, spi);
    pigpio_stop(pi);

    return xfer_count/2;    

}
