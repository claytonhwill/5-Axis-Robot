#This ensures REPL is available over USB
from machine import UART
import os
os.dupterm(None, 1)  # Disable REPL on UART0