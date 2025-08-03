import time
from servo import servo2040

def debug_log(message):
    """Centralized debug logging - works in both REPL and UART"""
    # First try to print to REPL (visible in your development environment)
    try:
        print(f"DEBUG: {message}")
    except:
        pass
    
    # Also send to UART if available
    #if uart:
    #    try:
    #        uart.write(f"DEBUG uart: {message}\n")
    #    except:
    #        pass
        
def read_current(hardware):
    """Read current with averaging for stability"""
    samples = 5
    total = 0
    hardware.mux.select(servo2040.CURRENT_SENSE_ADDR)
    for i in range(samples):
        current = hardware.cur_adc.read_current()
        total += current
        time.sleep(0.001)
    return total / samples

def handle_overload(hardware, current_reading, max_current, debug_log):
    """Handle overcurrent situation"""
    debug_log(f"OVERLOAD DETECTED! {current_reading:.2f}A > {max_current}A")
    overloaded = True
    
    # Disable all servos
    debug_log("Disabling servos...")
    hardware.disable_servos()
    
    # Wait for current to normalize
    debug_log("Waiting for current to normalize...")
    while True:
        current = read_current(hardware)
        debug_log(f"Current reading: {current:.2f}A")
        if current <= max_current * 0.8:
            break
        time.sleep(0.1)
    
    # Re-enable servos
    debug_log("Re-enabling servos")
    hardware.enable_servos()
    return False  # Overload cleared