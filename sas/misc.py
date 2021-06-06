
import logging

from PySide2 import QtCore, QtNetwork

from .client import SASClient

logger = logging.getLogger(__name__)

class CircuitBreaker(QtCore.QObject):

    def __init__(self, parent, initially_closed=True):
        self.parent = parent
        self.closed = initially_closed

        self.terminal_name_pairs = {}


    def isClosed(self):
        return self.closed

    
    def addTerminalPair1(self, input_terminal_name, output_terminal_name):
        self.terminal_pairs['1'] = (input_terminal_name, output_terminal_name)
        self.parent.input_terminals[input_terminal_name]['action'] = self.inputAction1

    def addTerminalPair2(self, input_terminal_name, output_terminal_name):
        self.terminal_pairs['2'] = (input_terminal_name, output_terminal_name)
        self.parent.input_terminals[input_terminal_name]['action'] = self.inputAction2
    
    def addTerminalPair3(self, input_terminal_name, output_terminal_name):
        self.terminal_pairs['3'] = (input_terminal_name, output_terminal_name)
        self.parent.input_terminals[input_terminal_name]['action'] = self.inputAction3

    # Hmmmm.... Same ugly solution as for the Relay?

    def inputAction1(self, new_state):
        input_terminal_name, output_terminal_name = self.terminal_name_pairs['1']
        if self.isClosed():
            output_state = new_state    # Could also be self.parent.getInputTerminalState(input_terminal_name)
        else:
            output_state = SASClient.no_state
        self.parent.setOutputTerminalState(output_terminal_name, output_state)

    def inputAction2(self, new_state):
        input_terminal_name, output_terminal_name = self.terminal_name_pairs['2']
        if self.isClosed():
            output_state = new_state    # Could also be self.parent.getInputTerminalState(input_terminal_name)
        else:
            output_state = SASClient.no_state
        self.parent.setOutputTerminalState(output_terminal_name, output_state)
    
    def inputAction3(self, new_state):
        input_terminal_name, output_terminal_name = self.terminal_name_pairs['3']
        if self.isClosed():
            output_state = new_state    # Could also be self.parent.getInputTerminalState(input_terminal_name)
        else:
            output_state = SASClient.no_state
        self.parent.setOutputTerminalState(output_terminal_name, output_state)

    


class Relay(QtCore.QObject):

    def __init__(self, parent, zero_state=SASClient.ac_power_off_state):
        self.parent = parent
        
        self.off_state = zero_state
        if zero_state == SASClient.ac_power_off_state:
            self.on_state = SASClient.ac_power_on_state
        elif zero_state == SASClient.dc_power_off_state:
            self.on_state = SASClient.dc_power_on_state

        self.coil_input_terminal_name = None
        self.no_terminal_name_pairs = {}
        self.nc_terminal_name_pairs = {}


    def currentInCoil(self):
        return self.parent.getInputTerminalState(self.coil_input_terminal_name) == self.on_state
        

    def addNormallyOpenTounge1(self, input_terminal_name, output_terminal_name):
        self.no_terminal_name_pairs['1'] = (input_terminal_name, output_terminal_name)
        self.parent.input_terminals[input_terminal_name]['action'] = self.inputActionNo1
    
    def addNormallyOpenTounge2(self, input_terminal_name, output_terminal_name):
        self.no_terminal_name_pairs['2'] = (input_terminal_name, output_terminal_name)
        self.parent.input_terminals[input_terminal_name]['action'] = self.inputActionNo2

    def addNormallyOpenTounge3(self, input_terminal_name, output_terminal_name):
        self.no_terminal_name_pairs['3'] = (input_terminal_name, output_terminal_name)
        self.parent.input_terminals[input_terminal_name]['action'] = self.inputActionNo3
    
    def addNormallyOpenTounge4(self, input_terminal_name, output_terminal_name):
        self.no_terminal_name_pairs['4'] = (input_terminal_name, output_terminal_name)
        self.parent.input_terminals[input_terminal_name]['action'] = self.inputActionNo4


    def inputActionNo1(self, new_state):
        input_terminal_name, output_terminal_name = self.no_terminal_name_pairs['1']
        if self.currentInCoil():
            output_state = new_state    # Could also be self.parent.getInputTerminalState(input_terminal_name)
        else:
            output_state = SASClient.no_state
        self.parent.setOutputTerminalState(output_terminal_name, output_state)
    
    def inputActionNo2(self, new_state):
        input_terminal_name, output_terminal_name = self.no_terminal_name_pairs['2']
        if self.currentInCoil():
            output_state = new_state    # Could also be self.parent.getInputTerminalState(input_terminal_name)
        else:
            output_state = SASClient.no_state
        self.parent.setOutputTerminalState(output_terminal_name, output_state)
    
    def inputActionNo3(self, new_state):
        input_terminal_name, output_terminal_name = self.no_terminal_name_pairs['3']
        if self.currentInCoil():
            output_state = new_state    # Could also be self.parent.getInputTerminalState(input_terminal_name)
        else:
            output_state = SASClient.no_state
        self.parent.setOutputTerminalState(output_terminal_name, output_state)
    
    def inputActionNo4(self, new_state):
        input_terminal_name, output_terminal_name = self.no_terminal_name_pairs['4']
        if self.currentInCoil():
            output_state = new_state    # Could also be self.parent.getInputTerminalState(input_terminal_name)
        else:
            output_state = SASClient.no_state
        self.parent.setOutputTerminalState(output_terminal_name, output_state)


    def addCoil(self, input_terminal_name, output_terminal_name):
        self.parent.registerInputTerminal(input_terminal_name, action=self.coilAction)
        self.parent.registerOutputTerminal(output_terminal_name, self.off_state)
        
        self.coil_input_terminal_name = input_terminal_name
        self.coil_output_terminal_name = output_terminal_name


    def coilAction(self, new_state):        # LOADACTION
        if new_state == self.on_state:
        # if self.currentInCoil():
            # Short all normally open tounges here
            for input_terminal_name, output_terminal_name in self.no_terminal_name_pairs.values():
                input_state = self.parent.getInputTerminalState(input_terminal_name)
                self.parent.setOutputTerminalState(output_terminal_name, input_state)
        else:
            # Open up all normally closed tounges here
            for input_terminal_name, output_terminal_name in self.no_terminal_name_pairs.values():
                self.parent.setOutputTerminalState(output_terminal_name, SASClient.no_state)

        if new_state == SASClient.no_state:

            

