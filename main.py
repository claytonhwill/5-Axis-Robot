import time
import sys
import gc
import os
from hardware import Hardware
from config_manager import ConfigManager
from communication import Communication
from utilities import debug_log, read_current, handle_overload
from modes.base_mode import BaseMode
from modes.home_mode import HomeMode
from modes.jog_mode import JogMode
from modes.playback_mode import PlaybackMode

# Enable garbage collection
gc.enable()
print("Catacomb Navigation Unit - Clayton W")
#os.dupterm(None, 1)  # Disable REPL on UART0

#if "main_running" in os.listdir():
#    print("main.py already running. Exiting.")
#    sys.exit()
#else:
#    with open("main_running", "w") as f:
#        f.write("1")
#        print("flagging main_running")
#        time.sleep(3)
#        f.write("0")

# Constants
MAX_CURRENT = 2.0
CURRENT_CHECK_INTERVAL = 250  # ms
STATUS_INTERVAL = 100  # ms
FRAME_RATE = 30

# Track if we've already run to prevent double execution
#if '_main_executed' in globals():
#    print("Preventing duplicate execution...")
#    sys.exit()
#_main_executed = True

# Debug function that works before hardware is initialized
def initial_debug(message):
    print(message)  # Fallback to print until UART is ready

# Initialize system
initial_debug("Starting system initialization...")

# Setup hardware
try:
    hardware = Hardware(initial_debug)
except Exception as e:
    print(f"Hardware init failed: {str(e)}")
    sys.exit()

# Setup config manager
try:
    #print("Calling config manager from main.py")
    config_manager = ConfigManager(hardware, lambda msg: debug_log(msg))
    #print("Calling config data from main.py")
    config_data = config_manager.load_config()
    #print("Calling create axes from main.py")
    config_manager.create_axes(config_data)
    #print("sequence data from main.py")
    sequence_data = config_manager.load_sequence()
except Exception as e:
    print(f"Config error: {str(e)}")
    sys.exit()

# Setup communication
try:
    comm = Communication(hardware, lambda msg: debug_log(msg))
    comm.requested_mode = None
except Exception as e:
    print(f"Comm init failed: {str(e)}")
    sys.exit()

# Setup modes
try:
    modes = [
        HomeMode(hardware, lambda msg: debug_log(msg)),
        JogMode(hardware, lambda msg: debug_log(msg)),
        PlaybackMode(hardware, lambda msg: debug_log(msg), sequence_data, FRAME_RATE)
    ]
    current_mode_index = 0
    current_mode = modes[current_mode_index]
except Exception as e:
    print(f"Mode init failed: {str(e)}")
    sys.exit()

# Enable hardware
try:
    hardware.enable_servos()
    debug_log("Servos enabled successfully")
except Exception as e:
    print(f"Servo enable failed: {str(e)}")
    sys.exit()

# Enter initial mode
try:
    current_mode.enter()
    debug_log(f"System ready | Mode: {current_mode.name}")
except Exception as e:
    print(f"Mode entry failed: {str(e)}")
    hardware.disable_servos()
    sys.exit()

# System state
last_button_state = False
press_start_time = 0
last_current_time = time.ticks_ms()
last_status_time = time.ticks_ms()
current_reading = 0.0
overloaded = False
loop_counter = 0

# Main loop
try:
    debug_log("Entering main loop")
    while True:
        loop_counter += 1
        #debug_log(f"Loop counter: {loop_counter}")
        
        # Process incoming commands
        comm.process_incoming()
            
        # Check for mode change request
        #debug_log("Checking for mode change requests")
        if comm.requested_mode is not None:
            requested = comm.requested_mode
            comm.requested_mode = None  # Reset flag
            
            if 0 <= requested < len(modes):
                # Exit current mode
                try:
                    current_mode.exit()
                except Exception as e:
                    debug_log(f"Mode exit error: {str(e)}")
                
                # Switch to requested mode
                current_mode_index = requested
                current_mode = modes[current_mode_index]
                
                # Enter new mode
                try:
                    current_mode.enter()
                    debug_log(f"Entered {current_mode.name} mode")
                except Exception as e:
                    debug_log(f"Mode enter error: {str(e)}")        


        # Handle button presses
        #debug_log(f"Checking for button presses")
        try:
            current_button = hardware.user_sw.raw()
            button_pressed = current_button and not last_button_state
            button_released = not current_button and last_button_state
            
            if button_pressed:
                debug_log(f"Button pressed in {current_mode.name} mode")
                press_start_time = time.ticks_ms()
            
            if button_released:
                press_duration = time.ticks_diff(time.ticks_ms(), press_start_time)
                debug_log(f"Button released after {press_duration}ms")
                
                # Short press: cycle modes
                if press_duration < 1000:
                    # Exit current mode
                    try:
                        current_mode.exit()
                    except Exception as e:
                        debug_log(f"Mode exit error: {str(e)}")
                    
                    # Switch to next mode
                    current_mode_index = (current_mode_index + 1) % len(modes)
                    current_mode = modes[current_mode_index]
                    
                    # Enter new mode
                    try:
                        current_mode.enter()
                        debug_log(f"Entered {current_mode.name} mode")
                    except Exception as e:
                        debug_log(f"Mode enter error: {str(e)}")
                
                # Long press: mode-specific action
                else:
                    try:
                        current_mode.handle_button_press(press_duration)
                    except Exception as e:
                        debug_log(f"Button handler error: {str(e)}")
            
            last_button_state = current_button
        except Exception as e:
            debug_log(f"Button processing error: {str(e)}")
        
        # Current monitoring
        #debug_log(f"Checking curent monitoring")
        try:
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, last_current_time) >= CURRENT_CHECK_INTERVAL:
                current_reading = read_current(hardware)  # Remove debug_log parameter
                last_current_time = current_time
                
                # Reset overload if current drops below threshold
                if overloaded and current_reading <= MAX_CURRENT:
                    debug_log("Current back to normal")
                    overloaded = False
                    hardware.enable_servos()  # Re-enable servos after overload
                    
                if current_reading > MAX_CURRENT and not overloaded:
                    # Pass debug_log lambda correctly
                    overloaded = handle_overload(
                        hardware, 
                        current_reading, 
                        MAX_CURRENT, 
                        lambda msg: debug_log(msg))
        except Exception as e:
            debug_log(f"Current monitor error: {str(e)}")
        
        # Status updates
        #debug_log(f"Status updates")
        try:
            current_time = time.ticks_ms()  # Update current time for status check
            if time.ticks_diff(current_time, last_status_time) >= STATUS_INTERVAL:
                # Get current frame for playback mode
                current_frame = current_mode.current_frame if hasattr(current_mode, 'current_frame') else 0
                total_frames = len(sequence_data)
                
                comm.send_status(current_mode, current_reading, overloaded, 
                                current_frame, total_frames)
                last_status_time = current_time
        except Exception as e:
            debug_log(f"Status update error: {str(e)}")
        
        # Update current mode
        try:
            current_mode.update()
        except Exception as e:
            debug_log(f"Mode update error: {str(e)}")
        
        # Small sleep to prevent watchdog issues
        time.sleep(0.01)
        
        # Periodic garbage collection
        if loop_counter % 100 == 0:
            gc.collect()

except KeyboardInterrupt:
    debug_log("Keyboard interrupt received")

except Exception as e:
    # Error handling
    debug_log(f"MAIN LOOP CRASH: {str(e)}")
    try:
        s = str(e)
        with open("error.log", "w") as f:
            f.write(s)
    except:
        pass

finally:
    # Shutdown procedure
    debug_log("Shutdown initiated")
    try:
        hardware.disable_servos()
        debug_log("All servos disabled")
    except:
        debug_log("Failed to disable servos")
    debug_log("System shutdown complete")
    #try:
    #    os.remove("main_running")
    #except:
    #    pass