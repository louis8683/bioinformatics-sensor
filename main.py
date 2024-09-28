from state import State, STATE_SETUP, STATE_ADVERTISE, STATE_DATA

class Activity:

    def __init__(self) -> None:
        pass
    
    def onFirstEnter():
        # the first time it enters this state
        pass

    def onBleDisconnected():
        # the BLE is disconnected
        pass

    

def setup(state: State):
    pass

def advertise(state: State):
    pass

def transmit_data(state: State):
    pass

# The default mode is always advertising mode
state = State()

# Main Loop 
# Looper, should show warning or throw error if blocked
# Benefits of using a main looper:
# 1. control the frequency of the MCU in one place
# 2. centralize the control of BLE connection and events
# Cons:
# 1. you'll have to pass the BLE object around
# Notes:
# - I'm basically treating the BLE as my UI, and the sensors as my database


# - The complexity arises when we add the setup mode into the mix
# - Without the setup mode, it is a simple two mode 
#    1. "AD" --[connect]--> "DATA"
#    2. "DATA" --[disconnect]--> "AD"
# - With the setup mode, it is more complicated
#    1. "AD" --[connect-data]--> "DATA"
#            --[connect-setup]--> "SETUP"
#    2. "DATA" --[disconnect]--> "AD" 
#    3. "SETUP" --[disconnect]--> "AD"

while True:

    if state.current == STATE_SETUP:
        # run setup
        setup(state)
    
    elif state.current == STATE_ADVERTISE:
        # run advertising
        advertise(state)

    elif state.current == STATE_DATA:
        # run data transmission
        transmit_data(state)

    else:
        except RuntimeError

