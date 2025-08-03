import json

class Communication:
    def __init__(self, hardware, debug_log):
        self.hardware = hardware
        self.debug_log = debug_log
        self.command_buffer = ""
        
    def process_incoming(self):
        while self.hardware.uart.any():
            #self.debug_log(f"Looking for incomming commands...")
            char = self.hardware.uart.read(1)
            if char == b'\n' or char == '\n':  # Handle both bytes and str
                #self.debug_log(f"Found an end char")
                self.process_command(self.command_buffer)
                self.command_buffer = ""
            elif char:
                try:
                    #self.debug_log(f"reveived a char: {char}")
                    # Handle both bytes and string
                    if isinstance(char, bytes):
                        char = char.decode('utf-8')
                    self.command_buffer += char
                except UnicodeError:
                    self.debug_log("Invalid character in command stream")
                    self.command_buffer = ""
            #self.debug_log(f"end of process_incoming")
    def process_command(self, cmd):
        self.debug_log(f"Received command: {cmd}")
        
        if cmd == "HOME_ALL":
            self.hardware.home_all_axes()
        elif cmd.startswith("HOME_AXIS:"):
            try:
                index = int(cmd.split(":")[1])
                if 0 <= index < len(self.hardware.axes):
                    self.hardware.home_single_axis(index)
                else:
                    self.debug_log(f"Invalid axis index: {index}")
            except ValueError:
                self.debug_log("Invalid HOME_AXIS command format")
        elif cmd == "RESTART_PLAYBACK":
            # Will be handled by mode
            pass
        # Add mode change command handling
        elif cmd.startswith("SET_MODE:"):
            try:
                mode_index = int(cmd.split(":")[1])
                # This should trigger a mode change in main.py
                self.debug_log(f"Mode change requested: {mode_index}")
                # We'll handle this in main.py by setting a flag
                self.requested_mode = mode_index
            except ValueError:
                self.debug_log("Invalid SET_MODE command format")
        else:
            self.debug_log(f"Unknown command: {cmd}")
            
    def send_status(self, current_mode, current_reading, overloaded, current_frame, total_frames):
        status = {
            "mode": current_mode.name,
            "axes": [],
            "current": current_reading,
            "overloaded": overloaded
        }
        
        # Add frame info only in PLAYBACK mode
        if current_mode.name == "PLAYBACK":
            status["frame"] = current_frame
            status["total_frames"] = total_frames
        
        for axis in self.hardware.axes:
            status["axes"].append({
                "name": axis["name"],
                "position": axis["servo"].value(),
                "min": axis["min"],
                "max": axis["max"],
                "home": axis["home"]
                })
            
        json_status = json.dumps(status)
        self.hardware.uart.write(("STATUS:" + json_status + "\n"))
        #self.hardware.uart.stdout.flush()