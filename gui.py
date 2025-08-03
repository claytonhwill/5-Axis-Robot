import tkinter as tk
import serial
import json
import threading
from tkinter import ttk, messagebox, scrolledtext
import time

class ServoControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Servo2040 Control Panel")
        self.root.geometry("1200x800")
        
        # Initialize axes list
        self.axes = []
        
        # Serial connection
        self.ser = None
        self.port_var = tk.StringVar(value="COM6")
        self.baudrate = 115200
        self.connected = False
        self.rx_count = 0
        self.tx_count = 0
        
        # Status variables
        self.conn_status_var = tk.StringVar(value="Disconnected")
        self.mode_var = tk.StringVar(value="Unknown")
        self.current_var = tk.StringVar(value="0.00A")
        self.frame_var = tk.StringVar(value="0/0")
        self.overload_var = tk.StringVar(value="Normal")
        
        # Terminal settings
        self.show_timestamps = tk.BooleanVar(value=True)
        self.show_rx = tk.BooleanVar(value=True)
        self.show_tx = tk.BooleanVar(value=True)
        self.terminal_max_lines = 200
        self.terminal_lines = 0
        self.filter_status = tk.BooleanVar(value=True)

        self.create_widgets()
        self.auto_connect()
    
    def auto_connect(self):
        """Try to connect to REPL ports"""
        ports = [
            'COM6',  # Windows
            '/dev/ttyACM0', '/dev/ttyACM1',   # Linux
            '/dev/cu.usbmodem'                # macOS
        ]
        
        for port in ports:
            try:
                self.ser = serial.Serial(port, baudrate=115200, timeout=1)
                self.connected = True
                self.conn_status_var.set("Connected")
                
                # Send a newline to wake up the REPL
                self.ser.write(b'\r\n')
                time.sleep(0.1)
                
                # Clear any initial output
                self.ser.flushInput()
                
                self.start_listening()
                self.log_message(f"Connected to REPL on {port}", "system")
                return
            except Exception as e:
                self.log_message(f"Connection failed: {str(e)}", "error")
                continue
        
        self.log_message("Auto-connect failed", "error")
    
    def create_widgets(self):
        # Main paned window for split view
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel for controls
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=2)
        
        # Right panel for terminal
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)
        
        # Build controls in left frame
        self.build_control_panel(left_frame)
        
        # Build terminal in right frame
        self.build_terminal_panel(right_frame)
    
    def build_control_panel(self, parent):
        # Top section: Connection and Mode
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Connection frame (left side)
        conn_frame = ttk.LabelFrame(top_frame, text="Connection")
        conn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Mode frame (right side)
        mode_frame = ttk.LabelFrame(top_frame, text="Mode Control")
        mode_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Populate connection frame
        self.build_connection_frame(conn_frame)

        
        
        # Populate mode frame
        self.build_mode_frame(mode_frame)

        safety_frame = ttk.LabelFrame(top_frame, text="Safety")
        safety_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))

        # populate safety frame
        self.build_safety_frame(safety_frame)

        # Axis control frame
        axis_frame = ttk.LabelFrame(parent, text="Axis Control")
        axis_frame.pack(fill=tk.BOTH, expand=True)
        self.create_axis_widgets(axis_frame)
    
        # Playback frame
        playback_frame = ttk.LabelFrame(parent, text="Playback Control")
        playback_frame.pack(fill=tk.X, pady=(0, 10))
        self.build_playback_frame(playback_frame)
        
        
    def build_connection_frame(self, parent):
        ttk.Label(parent, text="Port:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        port_entry = ttk.Entry(parent, textvariable=self.port_var, width=15)
        port_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Button(parent, text="Connect", command=self.connect).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(parent, text="Disconnect", command=self.disconnect).grid(row=0, column=3, padx=5, pady=2)
        
        # Connection status
        ttk.Label(parent, text="Status:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(parent, textvariable=self.conn_status_var, width=12).grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        
        # RX/TX counters
        ttk.Label(parent, text="RX:").grid(row=1, column=2, padx=(10, 0), pady=2)
        self.rx_label = ttk.Label(parent, text="0", width=5)
        self.rx_label.grid(row=1, column=3, padx=2, pady=2)
        
        ttk.Label(parent, text="TX:").grid(row=1, column=4, padx=(5, 0), pady=2)
        self.tx_label = ttk.Label(parent, text="0", width=5)
        self.tx_label.grid(row=1, column=5, padx=2, pady=2)
    
    def build_mode_frame(self, parent):
        # Current mode display
        ttk.Label(parent, text="Current Mode:").pack(padx=5, pady=2)
        ttk.Label(parent, textvariable=self.mode_var, font=("Arial", 12, "bold")).pack(padx=5, pady=5)
        
        # Mode buttons
        mode_buttons = ttk.Frame(parent)
        mode_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(mode_buttons, text="HOME", command=lambda: self.set_mode(0)).pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(mode_buttons, text="JOG", command=lambda: self.set_mode(1)).pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Button(mode_buttons, text="PLAYBACK", command=lambda: self.set_mode(2)).pack(side=tk.TOP, fill=tk.X, pady=2)
    
    def build_playback_frame(self, parent):
        # Frame information
        frame_info = ttk.Frame(parent)
        frame_info.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame_info, text="Frame:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(frame_info, textvariable=self.frame_var, width=12).grid(row=0, column=1, padx=5, pady=2)
        
        # Restart button
        ttk.Button(frame_info, text="Restart Playback", command=self.restart_playback).grid(row=0, column=2, padx=(20, 5), pady=2)
        
        # System status
        status_info = ttk.Frame(parent)
        status_info.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_info, text="Current:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(status_info, textvariable=self.current_var, width=8).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(status_info, text="Status:").grid(row=0, column=2, padx=(20, 5), pady=2, sticky=tk.W)
        ttk.Label(status_info, textvariable=self.overload_var, width=10).grid(row=0, column=3, padx=5, pady=2)
    
    def build_terminal_panel(self, parent):
        # Terminal frame
        terminal_frame = ttk.LabelFrame(parent, text="Terminal")
        terminal_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create terminal widget
        self.terminal = scrolledtext.ScrolledText(
            terminal_frame, 
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 10)
        )
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.terminal.tag_config("rx", foreground="blue")
        self.terminal.tag_config("tx", foreground="green")
        self.terminal.tag_config("system", foreground="black")
        self.terminal.tag_config("error", foreground="red")
        self.terminal.tag_config("status", foreground="purple")
        
        # Terminal controls frame
        ctrl_frame = ttk.Frame(terminal_frame)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Terminal controls
        ttk.Checkbutton(ctrl_frame, text="Timestamps", variable=self.show_timestamps).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(ctrl_frame, text="Show RX", variable=self.show_rx).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(ctrl_frame, text="Show TX", variable=self.show_tx).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(ctrl_frame, text="Hide STATUS", variable=self.filter_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Clear", command=self.clear_terminal).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Save Log", command=self.save_log).pack(side=tk.RIGHT, padx=5)

        legend_frame = ttk.Frame(terminal_frame)
        legend_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Create legend items
        legend_items = [
            ("System", "system", "black"),
            ("RX Data", "rx", "blue"),
            ("TX Data", "tx", "green"),
            ("Errors", "error", "red"),
            ("STATUS", "status", "purple")
        ]
        for text, tag, color in legend_items:
            frame = ttk.Frame(legend_frame)
            frame.pack(side=tk.LEFT, padx=5)
            ttk.Label(frame, text=text, foreground=color).pack(side=tk.LEFT)
            ttk.Label(frame, text="■", foreground=color, font=("Arial", 14)).pack(side=tk.LEFT, padx=(2, 5))
    
    def build_safety_frame(self, parent):
        # Moved current and status indicators
        status_info = ttk.Frame(parent)
        status_info.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(status_info, text="Current:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(status_info, textvariable=self.current_var, width=8).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(status_info, text="Status:").grid(row=0, column=2, padx=(20, 5), pady=2, sticky=tk.W)
        ttk.Label(status_info, textvariable=self.overload_var, width=10).grid(row=0, column=3, padx=5, pady=2)
        
        # NEW: Safety buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Button(button_frame, text="INTERRUPT", 
                  command=self.interrupt, 
                  style="Emergency.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        ttk.Button(button_frame, text="SOFT RESET", 
                  command=self.soft_reset).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Create emergency button style
        style = ttk.Style()
        style.configure("Emergency.TButton", foreground="white", background="red")
    
    def interrupt(self):
        if self.connected:
            try:
                # Ctrl+C is ASCII code 3
                self.ser.write(b'\x03')
                self.tx_count += 1
                self.tx_label.config(text=str(self.tx_count))
                self.log_message("Sent: INTERRUPT (Ctrl+C)", "tx")
            except Exception as e:
                self.log_message(f"Error sending interrupt: {str(e)}", "error")
    
    def soft_reset(self):
        if self.connected:
            try:
                # Ctrl+D is ASCII code 4
                self.ser.write(b'\x04')
                self.tx_count += 1
                self.tx_label.config(text=str(self.tx_count))
                self.log_message("Sent: SOFT RESET (Ctrl+D)", "tx")
            except Exception as e:
                self.log_message(f"Error sending soft reset: {str(e)}", "error")

    def create_axis_widgets(self, parent):
        # Create vertical layout for axes (stacked)
        for i in range(5):  # 5 axes
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, padx=10, pady=5, anchor=tk.W)
            
            # Axis name and position
            name_var = tk.StringVar(value=f"Axis {i+1}")
            pos_var = tk.StringVar(value="0.00°")
            
            ttk.Label(frame, textvariable=name_var, width=8).grid(row=0, column=0, padx=5, sticky=tk.W)
            
            ttk.Label(frame, text="Position:").grid(row=0, column=1, padx=5)
            ttk.Label(frame, textvariable=pos_var, width=8).grid(row=0, column=2, padx=5)
            
            # Progress bar showing position in range
            progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=200, mode='determinate')
            progress.grid(row=0, column=3, padx=10)
            
            # Home button
            ttk.Button(frame, text="Home", width=8, command=lambda idx=i: self.home_axis(idx)).grid(row=0, column=4, padx=5)
            
            # Store references
            self.axes.append({
                "name": name_var,
                "position": pos_var,
                "progress": progress,
                "min": -90,
                "max": 90
            })
    
    def log_message(self, message, msg_type="system"):
        """Add a message to the terminal with color coding"""
        if not self.terminal:
            return
            
        # Apply filters
        if msg_type == "rx" and not self.show_rx.get():
            return
        if msg_type == "tx" and not self.show_tx.get():
            return
        if msg_type == "rx" and self.filter_status.get() and "STATUS:" in message:
            return
            
        # Get timestamp
        timestamp = ""
        if self.show_timestamps.get():
            timestamp = time.strftime("%H:%M:%S") + " "
        
        # Format message
        formatted_msg = f"{timestamp}{message}\n"
        
        # Add to terminal
        self.terminal.configure(state=tk.NORMAL)
        
        # Limit lines to prevent memory issues
        self.terminal_lines += 1
        if self.terminal_lines > self.terminal_max_lines:
            self.terminal.delete(1.0, 2.0)
            self.terminal_lines -= 1
        
        if "STATUS:" in message and msg_type == "rx":
            self.terminal.insert(tk.END, formatted_msg, "status")
        else:
            self.terminal.insert(tk.END, formatted_msg, msg_type)
        self.terminal.see(tk.END)
        self.terminal.configure(state=tk.DISABLED)
    
    def clear_terminal(self):
        """Clear the terminal window"""
        self.terminal.configure(state=tk.NORMAL)
        self.terminal.delete(1.0, tk.END)
        self.terminal.configure(state=tk.DISABLED)
        self.terminal_lines = 0
    
    def save_log(self):
        """Save terminal content to a log file"""
        try:
            with open("servo_log.txt", "w") as f:
                f.write(self.terminal.get(1.0, tk.END))
            self.log_message("Log saved to servo_log.txt", "system")
        except Exception as e:
            self.log_message(f"Error saving log: {str(e)}", "error")
    
    def update_axis(self, axis_data):
        for i, axis in enumerate(axis_data):
            if i < len(self.axes):
                # Update name if needed
                if axis["name"] != self.axes[i]["name"].get():
                    self.axes[i]["name"].set(axis["name"])
                
                # Update position
                pos = axis["position"]
                self.axes[i]["position"].set(f"{pos:.1f}°")
                
                # Update progress bar
                min_val = axis["min"]
                max_val = axis["max"]
                range_val = max_val - min_val
                if range_val > 0:
                    progress = ((pos - min_val) / range_val) * 100
                    self.axes[i]["progress"]["value"] = progress
                
                # Store min/max for future reference
                self.axes[i]["min"] = min_val
                self.axes[i]["max"] = max_val
    
    def process_status(self, status):
        try:
            # Handle both string and dictionary status
            if isinstance(status, str):
                if status.startswith("STATUS:"):
                    try:
                        status = json.loads(status[7:])
                    except:
                        self.log_message("Invalid JSON status", "error")
                        return
                else:
                    return  # Not a status message
            
            # Now process as dictionary
            self.mode_var.set(status.get("mode", "Unknown"))
            self.current_var.set(f"{status.get('current', 0):.2f}A")
            
            # Handle frame information
            if "frame" in status and "total_frames" in status:
                self.frame_var.set(f"{status['frame']}/{status['total_frames']}")
            else:
                self.frame_var.set("N/A")
            
            # Handle overload status
            if "overloaded" in status:
                self.overload_var.set("Overload!" if status["overloaded"] else "Normal")
            else:
                self.overload_var.set("Unknown")
            
            # Update axes information
            if "axes" in status:
                self.update_axis(status["axes"])
        except Exception as e:
            self.log_message(f"Error processing status: {str(e)}", "error")
    
    def start_listening(self):
        def serial_listener():
            while self.connected:
                try:
                    if self.ser.in_waiting:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.rx_count += 1
                            self.rx_label.config(text=str(self.rx_count))
                            
                            # Log to terminal
                            self.log_message(line, "rx")
                            
                            # Process STATUS messages
                            if line.startswith("STATUS:"):
                                json_str = line[7:]
                                try:
                                    status = json.loads(json_str)
                                    self.root.after(0, lambda s=status: self.process_status(s))
                                except json.JSONDecodeError:
                                    self.log_message(f"Invalid JSON: {json_str}", "error")
                except Exception as e:
                    self.connected = False
                    self.conn_status_var.set("Disconnected")
                    self.log_message(f"Connection lost: {str(e)}", "error")
                    break
        
        threading.Thread(target=serial_listener, daemon=True).start()
    
    def send_command(self, command):
        if self.connected:
            try:
                self.ser.write((command + "\n").encode('utf-8'))
                self.tx_count += 1
                self.tx_label.config(text=str(self.tx_count))
                self.log_message(command, "tx")
            except Exception as e:
                self.log_message(f"Send error: {str(e)}", "error")
    
    def connect(self):
        port = self.port_var.get()
        if not port:
            self.log_message("Please specify a port", "error")
            return
        
        try:
            self.ser = serial.Serial(port, self.baudrate, timeout=1)
            self.connected = True
            self.conn_status_var.set("Connected")
            self.start_listening()
            self.log_message(f"Connected to {port}", "system")
        except serial.SerialException as e:
            self.log_message(f"Connection failed: {str(e)}", "error")
    
    def disconnect(self):
        if self.connected:
            try:
                self.ser.close()
                self.connected = False
                self.conn_status_var.set("Disconnected")
                self.log_message("Disconnected", "system")
            except Exception as e:
                self.log_message(f"Disconnect error: {str(e)}", "error")
    
    def home_all(self):
        self.log_message("Sending: HOME_ALL", "tx")
        self.send_command("HOME_ALL")
    
    def home_axis(self, index):
        self.log_message(f"Sending: HOME_AXIS:{index}", "tx")
        self.send_command(f"HOME_AXIS:{index}")
    
    def set_mode(self, mode_index):
        self.log_message(f"Sending: SET_MODE:{mode_index}", "tx")
        self.send_command(f"SET_MODE:{mode_index}")
    
    def restart_playback(self):
        self.log_message("Sending: RESTART_PLAYBACK", "tx")
        self.send_command("RESTART_PLAYBACK")

if __name__ == "__main__":
    root = tk.Tk()
    app = ServoControlGUI(root)
    root.mainloop()