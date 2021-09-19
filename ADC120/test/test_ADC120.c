#include "ADC120.h"
#include <stdio.h>
#include <time.h>

void sleep_ms(int ms) 
{
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000;
    nanosleep(&ts, NULL);
}

int main(int argc, char* argv[])
{
    if (ADC120_init() != 0) {
        return 1;
    }

    int const baud = 1000000;
    // int const nreads = 2;
    // for (int ch = 0; ch < 8; ++ch) {
    //     for (int n = 0; n < nreads; ++n) {
    //         printf("Reading channel %d (%d)... ",ch, n+1); 
    //         float const v = ADC120_read(ch, baud);
    //         printf("%1.4f\n", v);
    //     }
    //     sleep_ms(500);
    // }

    int const num_ch = 16;
    int ch_list[]    = {1, 1, 1, 1, 1, 1, 1, 1, 7, 7, 7, 7, 7, 7, 7, 7};
    float val_list[] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    
    int num_read = ADC120_readn(num_ch, ch_list, val_list, baud);

    if (num_read != num_ch) {
        fprintf(stderr,"Failed to read all channels in list.\n");
    } else {
        printf("Ch | Raw\n");
        printf("---+-------\n");

        for (int i = 0; i < num_ch; ++i) {
            printf(" %d : %6.4f\n",ch_list[i], val_list[i]);
        }
    }


    printf("Done");
    return 0;

}
