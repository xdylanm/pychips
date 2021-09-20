from time import sleep

class MAX31856:
    class TcType:
        """Thermocouple types"""
        B = 0b0000
        E = 0b0001
        J = 0b0010
        K = 0b0011
        N = 0b0100
        R = 0b0101
        S = 0b0110
        T = 0b0111
        G8 = 0b1000
        G32 = 0b1101

    class RegAddr:
        """MAX31856 register addresses for read (mask with 0x7F).
        To write, set the write bit with (0x80 | addr)"""
        CR0 = 0x00
        CR1 = 0x01
        MASK = 0x02
        CJHF = 0x03
        CJLF = 0x04
        LTHFTH = 0x05
        LTHFTL = 0x06
        LTLFTH = 0x07
        LTLFTL = 0x08
        CJTO = 0x09
        CJTH = 0x0A
        CJTL = 0x0B
        LTCBH = 0x0C
        LTCBM = 0x0D
        LTCBL = 0x0E
        SR = 0x0F

    class RegCR0: 
        """MAX31856 control register 0 (CR0) fields"""
        AUTOCONVERT = 0x80
        ONESHOT = 0x40
        OCFAULT1 = 0x20
        OCFAULT0 = 0x10
        CJ = 0x08
        FAULT = 0x04
        FAULTCLR = 0x02

    class RegSR:
        """MAX31856 status register (SR) fields"""
        CJ_RANGE = 0x80
        TC_RANGE = 0x40
        CJ_HIGH = 0x20
        CJ_LOW = 0x10
        TC_HIGH = 0x08
        TC_LOW = 0x04
        OVUV = 0x02
        OPEN = 0x01
 
    def __init__(self, spi, thermocouple_type=TcType.K):
        self._device = spi
        self.thermocouple_type = thermocouple_type

        # assert on any fault
        print("Clearing MASK reg")
        self._write_byte(self.RegAddr.MASK, 0x0)
        # config for open circuit faults
        print("Set OC fault detection")
        self._write_byte(self.RegAddr.CR0, self.RegCR0.OCFAULT0)

        print("Configure for thermocouple type")
        data_CR1 = self._read_reg(self.RegAddr.CR1)[0]
        #print("  Read CR1: {0:2x}".format(data_CR1))
        data_CR1 &= 0xF0
        data_CR1 |= int (thermocouple_type) & 0x0F
        #print("  Writing CR1: {0:2x}".format(data_CR1))
        self._write_byte(self.RegAddr.CR1, data_CR1)
        #data_CR1 = self._read_reg(self.RegAddr.CR1)[0]
        #print("  Readback CR1: {0:2x}".format(data_CR1))

        print("init complete")

    def start_conversion(self):
        """Start a temperature conversion from the probe with no delay. Caller"""
        """is responsible for allowing enough time before read out (170ms typ)"""
        self._trigger_one_shot(0)

    def read_temperature_reg(self):
        # read three bytes (high, mid, low)
        raw_bytes = self._read_reg(self.RegAddr.LTCBH,3)
        raw_val = (raw_bytes[0] << 16) + (raw_bytes[1] << 8) + raw_bytes[2]
        return raw_val / 4096.0

    @property
    def temperature(self):
        """Trigger a conversion and read the resulting temperature after a delay"""
        self._trigger_one_shot(250)
        return self.read_temperature_reg()

    @property
    def ref_temperature(self):
        self._trigger_one_shot(250)

        # read two bytes (high, low)
        raw_bytes = self._read_reg(self.RegAddr.CJTH,2)
        raw_val = (raw_bytes[0] << 8) + raw_bytes[1]
        return raw_val / 256.0

    @property
    def temperature_fault_thresholds(self):
        """Read values in linearized tempeature high/low fault threshold registers.
        Returns a 2-tuple with (low fault threshold, high fault threshold)"""
        # read two bytes (high, low)
        lo_fault_val = self._convert_threshold_temperature_from_reg(self._read_reg(self.RegAddr.LTLFTH,2))
        hi_fault_val = self._convert_threshold_temperature_from_reg(self._read_reg(self.RegAddr.LTHFTH,2))
        return (lo_fault_val, hi_fault_val)

    @temperature_fault_thresholds.setter
    def temperature_fault_thresholds(self,val):
        """Set the linearized tempeature high/low fault threshold registers.
        Input is a 2-tuple of floats with (low fault threshold, high fault threshold)"""
        if len(val) is not 2:
            raise ValueError("Expecting a tuple with low and high temperature thresholds")
        if abs(val[0]) > 2047 or abs(val[1]) > 2047:
            raise ValueError("The temperature threshold is out of range")
        
        int_val_lo = self._convert_threshold_temperature_to_reg(val[0])
        int_val_hi = self._convert_threshold_temperature_to_reg(val[1])

        self._write_byte(self.RegAddr.LTLFTL, int_val_lo & 0xFF)
        self._write_byte(self.RegAddr.LTLFTH, (int_val_lo >> 8) & 0xFF)
        
        self._write_byte(self.RegAddr.LTHFTL, int_val_hi & 0xFF)
        self._write_byte(self.RegAddr.LTHFTH, (int_val_hi >> 8) & 0xFF)

    def faults(self):
        faults = self._read_reg(self.RegAddr.SR)[0]
        
        return {
            "CJ_RANGE" : bool(self.RegSR.CJ_RANGE & faults),
            "TC_RANGE" : bool(self.RegSR.TC_RANGE & faults),
            "CJ_HIGH" : bool(self.RegSR.CJ_HIGH & faults),
            "CJ_LOW" : bool(self.RegSR.CJ_LOW & faults),
            "TC_HIGH" : bool(self.RegSR.TC_HIGH & faults),
            "TC_LOW" : bool(self.RegSR.TC_LOW & faults),
            "OVUV" : bool(self.RegSR.OVUV & faults),
            "OPEN" : bool(self.RegSR.OPEN & faults)}

    def clear_faults(self):
        self._trigger_one_shot(250)    # update last stored T
        data_CR0 = self._read_reg(self.RegAddr.CR0)[0]
        data_CR0 |= self.RegCR0.FAULTCLR
        print("Clear faults: CR0={:8b}".format(data_CR0 & 0xFF))
        self._write_byte(self.RegAddr.CR0, data_CR0)

    def _convert_threshold_temperature_from_reg(self,raw_bytes):
        """The input 'raw_bytes' is ordered (high, low). Values are stored in two 
        adjacent bytes (high & low) in a decimal format: the 4 LSBs of the 2-byte 
        word are the decimal, and the MSB is the sign bit"""
        val = (raw_bytes[0] << 8) + raw_bytes[1]
        return (-1.0 if (val & 0x8000) else 1.0) * ((val & 0x7FFF) / 16.0)


    def _convert_threshold_temperature_to_reg(self, val):
        return (int(abs(val)*16) & 0x7FFF) | (0x8000 if val < 0. else 0x0000)

    def _trigger_one_shot(self, ms_delay):
        self._write_byte(self.RegAddr.CJTO, 0x00)

        data_CR0 = self._read_reg(self.RegAddr.CR0)[0]
        data_CR0 &= ~self.RegCR0.AUTOCONVERT
        data_CR0 |=  self.RegCR0.ONESHOT
        self._write_byte(self.RegAddr.CR0, data_CR0)
        if ms_delay > 0:
            sleep(ms_delay/1000.)

    def _write_byte(self,addr,data):
        to_send = [(0x80 | addr) & 0xFF, data & 0xFF]
        with self._device as spi:
            spi.xfer2(to_send)
    
    def _read_reg(self, addr, count=1):
        buf = [0x7F & addr] + [0x00 for i in range(count)]
        with self._device as spi:
            spi.xfer2(buf)
        return buf[1:]   

