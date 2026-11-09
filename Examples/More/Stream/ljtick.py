import time
from labjack import ljm

# --- CONFIGURATION ---
# Open connection to the first found T-series LabJack
handle = ljm.openS("ANY", "ANY", "ANY") 

# Configure your specific LJTick-InAmp hardware settings
GAIN = 51.0       # Standard jumpers are 11.0, 51.0, or 201.0
OFFSET = 1.25     # Default factory offset is 1.25V
AIN_CHANNEL = "AIN0"  # Terminal where the LJTick-InAmp VOUT is plugged in

def get_inamp_voltage(handle, channel, gain, offset):
    """Reads the modified analog voltage and calculates the true input voltage."""
    # 1. Read the raw amplified/offset voltage from the LabJack ADC
    v_out = ljm.eReadName(handle, channel)
    
    # 2. Reverse the LJTick-InAmp transfer function math
    v_in = (v_out - offset) / gain
    return v_in

try:
    print("Reading true sensor voltages. Press Ctrl+C to stop...\n")
    while True:
        true_voltage = get_inamp_voltage(handle, AIN_CHANNEL, GAIN, OFFSET)
        
        # Note: If using a K-type thermocouple, you would now pass 
        # true_voltage into a thermocouple conversion formula or look-up table.
        print(f"Measured True Signal Input: {true_voltage:0.6f} V")
        
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nStopping data acquisition.")

finally:
    # Always close the device safely
    ljm.close(handle)
