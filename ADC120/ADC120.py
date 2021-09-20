
class ADC120:
    """
    8-channel, 50 ksps to 1 Msps, 12-bit A/D converter
    
    12 bit read initiated by writing channel address
    bit:   0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
    write: X  X  A2 A1 A0 X  X  X  X  X  X  X  X  X  X  X
    read:  0  0  0  0  B11B10B9 ..................B2 B1 B0

    Note: Capacitance during track is 45pF per datasheet. Large
    impedance inputs (>10k) will give a time constant >1us -- too
    slow to settle during T_acq = 3*t_sclk. It seems that at idle,
    the ADC120 samples Ch0, so a high Z input will result in
    something like V_0 being held the first read. In that case, 
    a dual read (see read_with_delay(acq_delay=1)) will give a better
    result on the second output.
    """

    def __init__(self, spi):
        self._device = spi

    def read(self, ch):
        return self.read_with_delay(ch,0)

    def read_with_delay(self,ch,acq_delay=0):
        if ch < 0 or ch > 7:
            raise RuntimeError("ADC channel {} out of range".format(ch))
        
        addr = 0b00111000 & (ch << 3)
        buf = [0x00 for i in range(2*(acq_delay+1))]
        for i in range(1+acq_delay): 
            buf[2*i] = addr

        with self._device as spi:
            spi.xfer2(buf)
        
        result = (((buf[-2] & 0x0F) << 8) + buf[-1])/4095.0
        return result

    def readn(self, ch):
        if any([i < 0 or i > 7 for i in ch]):
            raise RuntimeError("ADC channel in list is out of range")
            
        buf = [0x00] * 2 * len(ch)
        for i, chi in enumerate(ch):
            buf[2*i] = 0b00111000 & (chi << 3)

        with self._device as spi:
            spi.xfer2(buf)
        
        result = [(((buf[2*i] & 0x0F) << 8) + buf[2*i+1])/4095.0 for i in range(len(ch))]
        return result

    def send_raw(self, byte):
        buf = [0xFF & byte, 0x00]
        with self._device as spi:
            spi.xfer2(buf)
        return buf

