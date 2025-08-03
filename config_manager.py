from servo import Calibration, Servo, servo2040
import time
import json
import uos

class ConfigManager:
    def __init__(self, hardware, debug_log):
        print("__init__ of config manager")
        self.hardware = hardware
        self.debug_log = debug_log
        
    def load_config(self):
        self.debug_log("Loading configuration...")
        filename='config.json'
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
                self.debug_log(f"Loaded config: {len(config)} axes")
                return config
        except Exception as e:
            self.debug_log(f"Config error: {str(e)}")
            # Create default config
            default_config = [
                {"name": f"Axis {i+1}", "pin": i, 
                 "min_value": -90, "max_value": 90, 
                 "home_value": 0, "sensor_addr": i}
                for i in range(5)
            ]
            self.debug_log("Using default configuration")
            return default_config
            
    def create_axes(self, config_data):
        self.debug_log("Creating axes from configuration...")
        for i, cfg in enumerate(config_data):
            # Create calibration
            cal = Calibration()
            cal.apply_two_pairs(1000, 2000, cfg["min_value"], cfg["max_value"])
            self.debug_log(f"  Calibration for {cfg['name']}: min={cfg['min_value']}°, max={cfg['max_value']}°")
            
            # Create servo
            servo = Servo(cfg["pin"], cal)
            
            # Get sensor address (default to index)
            sensor_addr = cfg.get("sensor_addr", i)
            
            self.hardware.axes.append({
                "name": cfg["name"],
                "servo": servo,
                "home": cfg["home_value"],
                "min": cfg["min_value"],
                "max": cfg["max_value"],
                "sensor_addr": sensor_addr
            })
            self.debug_log(f"  Created axis {i}: {cfg['name']} on pin {cfg['pin']}, sensor: {sensor_addr}")
            
        self.debug_log("All axes created")
        
    def load_sequence(self, filename='sequence.csv'):
        self.debug_log("Loading sequence...")
        sequence = []
        try:
            if filename in uos.listdir():
                with open(filename, 'r') as f:
                    for line_num, line in enumerate(f):
                        try:
                            frame = [float(x.strip()) for x in line.split(',')]
                            if len(frame) == len(self.hardware.axes):
                                sequence.append(frame)
                            else:
                                self.debug_log(f"Invalid frame on line {line_num}: expected {len(self.hardware.axes)} values, got {len(frame)}")
                        except ValueError:
                            self.debug_log(f"Invalid number in frame on line {line_num}")
                    self.debug_log(f"Loaded sequence: {len(sequence)} frames")
            else:
                self.debug_log(f"Sequence file {filename} not found")
        except Exception as e:
            self.debug_log(f"Sequence error: {str(e)}")
        return sequence