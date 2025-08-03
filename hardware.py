from machine import Pin, UART
from pimoroni import Analog, AnalogMux, Button
from servo import Servo, Calibration, servo2040
import time
import sys
import io
import uselect

class Hardware:
    def __init__(self, debug_log):
        self.debug_log = debug_log
        #self.initialize_uart()
        self.initialize_repl()
        self.initialize_analog()
        self.initialize_servo_components()
    
    def initialize_repl(self):
        self.debug_log("Initializing REPL communication...")
        
        # Create a UART-like interface using stdin/stdout
        class REPL_IO:
            def __init__(self):
                self.stdin = sys.stdin
                self.stdout = sys.stdout
                self.poll = uselect.poll()
                self.poll.register(sys.stdin, uselect.POLLIN)
                
            def any(self):
                return self.poll.poll(0)  # Always assume data might be available
                
            def read(self, size=1):
                return self.stdin.read(size) if self.any() else b''
                
            def write(self, data):
                return self.stdout.write(data)
                
        self.uart = REPL_IO()
        self.debug_log("REPL communication initialized")
        
    def initialize_uart(self):
        self.debug_log("Initializing UART communication...")
        self.uart = UART(0, baudrate=115200)
        self.debug_log("UART communication initialized")
        
    def initialize_analog(self):
        self.debug_log("Initializing analog components...")
        self.sen_adc = Analog(servo2040.SHARED_ADC)
        self.cur_adc = Analog(servo2040.SHARED_ADC, servo2040.CURRENT_GAIN,
                              servo2040.SHUNT_RESISTOR, servo2040.CURRENT_OFFSET)
        self.mux = AnalogMux(servo2040.ADC_ADDR_0, servo2040.ADC_ADDR_1, servo2040.ADC_ADDR_2,
                             muxed_pin=Pin(servo2040.SHARED_ADC))
        self.user_sw = Button(servo2040.USER_SW)
        self.debug_log("Analog components initialized")
        
    def initialize_servo_components(self):
        self.debug_log("Initializing servo components...")
        # Servo objects will be created in config manager
        self.axes = []
        self.debug_log("Servo components ready")
        
    def enable_servos(self):
        self.debug_log("Enabling servos...")
        for axis in self.axes:
            axis["servo"].enable()
        self.debug_log("All servos enabled")
        
    def disable_servos(self):
        self.debug_log("Disabling servos...")
        for axis in self.axes:
            axis["servo"].disable()
        self.debug_log("All servos disabled")
        
    def home_all_axes(self):
        self.debug_log("Homing all axes...")
        for axis in self.axes:
            self.debug_log(f"  Homing {axis['name']} to {axis['home']}°")
            axis["servo"].value(axis["home"])
        time.sleep(1)
        self.debug_log("Homing complete")
        
    def home_single_axis(self, index):
        axis = self.axes[index]
        self.debug_log(f"Homing axis {index} ({axis['name']}) to {axis['home']}°")
        axis["servo"].value(axis["home"])