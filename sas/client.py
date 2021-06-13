
import logging

from functools import partial

from PySide2 import QtCore, QtNetwork

logger = logging.getLogger(__name__)


class SASClient2(QtCore.QObject):

    ac_230_on_state = '230VAC'
    ac_230_off_state = '0VAC'
    dc_48_on_state = '48VDC'
    dc_48_off_state = '0VDC'
    dc_12_on_state = '12VDC'
    dc_12_off_state = '0VDC'
    dc_5_on_state = '5VDC'
    dc_5_off_state = '0VDC'

    # signal_on_state = '12VDC'
    # signal_off_state = '0VDC'
    
    no_state = 'None'

    def __init__(self):
        super(SASClient2, self).__init__()

        self.client_name = 'default'

        # self.input_terminals = {}
        # self.output_terminals = {}

        self.terminals = {}

        self.server_address = '127.0.0.1'
        self.server_port = 23456

        self.socket = QtNetwork.QTcpSocket()
        self.socket.connected.connect(self.onConnected)
        self.socket.disconnected.connect(self.onDisconnected)
        self.socket.error.connect(self.onError)
        self.socket.stateChanged.connect(self.onStateChanged)
        self.socket.readyRead.connect(self.onReadyRead)

    def setClientName(self, name):
        self.client_name = name

    def onReadyRead(self):
        received_message = self.socket.readAll().data().decode()
        
        # logger.debug('Received message from connection %s: "%s"' % (socket_id, received_message.rstrip()))
        
        lines = received_message.split('\n')

        for line in lines:
            entries = line.split(':')
            if len(entries) > 1:
                if entries[0] == 'statechange':
                    terminal_name = entries[1]
                    new_state = entries[2]

                    self.registerTerminalState(terminal_name, new_state)
                    
                else:
                    raise Exception


    def startClient(self):

        # Hmmmm.... Do the connecting in a thread instead...... 

        logger.debug('Connecting to host at %s, port %d' % (self.server_address, self.server_port))
        self.socket.connectToHost('127.0.0.1', 23456)
        self.socket.waitForConnected()


    def onConnected(self):
        logger.debug('Connected to host at %s, port %d' % (self.server_address, self.server_port))

        self.pushClientName()
        self.pushTerminals()
        # self.remoteRegisterInputTerminals()
        # self.remoteRegisterOutputTerminals()

        # self.propagateSources()

       
    def onDisconnected(self):
        logger.debug('Disconnected from host at %s, port %d' % (self.server_address, self.server_port))
        # self.startClient()

        # self.deRegisterOutputTerminals()
        # self.deRegisterInputTerminals()


    def onError(self, error):
        logger.debug('Socket error occured: %s' % error)
        if error == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            self.startClient()


    def onStateChanged(self, state):
        logger.debug('Socket state changed to %s' % state)

    def defaultTerminalAction(self, terminal_name, new_state):
        self.terminals[terminal_name]['state'] = new_state
        """
        Push the terminals local state to the server.
        """
        self.pushTerminalState(terminal_name, new_state)


    def registerTerminal(self, terminal_name, source=False, state=no_state):
        self.terminals[terminal_name] = {'name': terminal_name, 'state': state, 'action': partial(self.defaultTerminalAction, terminal_name)}

    def getTerminalState(self, terminal_name):
        return self.terminals[terminal_name]['state']

    def registerTerminalState(self, terminal_name, new_state):
        """
        Registers a state change that was received from the server side.
        """
        logger.debug('Received statechange request on %s (new state: %s) from server' % (terminal_name, new_state))
        # Register the new state locally, but only if it differs from the old state.
        if self.getTerminalState(terminal_name) != new_state:# or self.getTerminalState(terminal_name) == self.no_state:
            #self.terminals[terminal_name]['state'] = new_state
        
            # Perform action due to new state.
            logger.debug('Registered statechange on %s (new state: %s)' % (terminal_name, new_state))
            self.terminals[terminal_name]['action'](new_state)
            


    def pushTerminalState(self, terminal_name, new_state):
        message = 'statechange:' + ':'.join((terminal_name, new_state)) + '\n'
        self.socket.write(message.encode())
        logger.debug('Sent statechange on %s (new state: %s) to server' % (terminal_name, new_state))

    # def registerInputTerminal(self, name, action=None):
    #     self.input_terminals[name] = {'name': name, 'state': self.no_state, 'action': action}


    # def registerOutputTerminal(self, name, state=no_state):
    #     self.output_terminals[name] = {'name': name, 'state': state}


    # def getOutputTerminalState(self, name):
    #     return self.output_terminals[name]['state']


    # def setOutputTerminalState(self, name, new_state):
    #     if self.getOutputTerminalState(name) != new_state:
    #         self.output_terminals[name]['state'] = new_state
    #         self.remoteSendOutputTerminalState(name, new_state)


    # def getInputTerminalState(self, name):
    #     return self.input_terminals[name]['state']


    # def setInputTerminalState(self, name, new_state):
    #     if self.getInputTerminalState(name) != new_state:
    #         self.input_terminals[name]['state'] = new_state
    #         if self.input_terminals[name]['action']:
    #             self.input_terminals[name]['action'](new_state)


    def pushClientName(self):
        message = 'clientname:' + self.client_name + '\n'
        self.socket.write(message.encode())
        logger.debug('Sent client name registration to server (%s).' % (self.client_name, ))


    def pushTerminals(self):
        if len(self.terminals) > 0:
            message = 'registration:' + ':'.join(self.terminals) + '\n'
            self.socket.write(message.encode())
            logger.debug('Registered terminals on server (%s).' % (', '.join(self.terminals)))


    # def remoteRegisterOutputTerminals(self):
    #     if len(self.output_terminals) > 0:
    #         message = 'registration:' + 'outputs:' + ':'.join(self.output_terminals) + '\n'
    #         self.socket.write(message.encode())
    #         logger.debug('Registered output terminals on server (%s).' % (', '.join(self.output_terminals)))


    # def pushTerminalState(self, terminal_name, new_state):
    #     message = 'statechange:' + ':'.join((terminal_name, new_state)) + '\n'
    #     self.socket.write(message.encode())
    #     logger.debug('Sent statechange on %s (new state: %s) to server' % (terminal_name, new_state))


    def deRegisterOutputTerminals(self):
        pass
        """NOOOOOOOOOOOOOO"""


    def deRegisterInputTerminals(self):
        pass
    



class SASClient(QtCore.QObject):

    ac_power_on_state = '230VAC'
    ac_power_off_state = '0VAC'
    dc_power_on_state = '48VDC'
    dc_power_off_state = '0VDC'
    signal_on_state = '12VDC'
    signal_off_state = '0VDC'
    no_state = 'None'

    def __init__(self):
        super(SASClient, self).__init__()

        self.client_name = 'default'

        self.input_terminals = {}
        self.output_terminals = {}

        self.server_address = '127.0.0.1'
        self.server_port = 23456

        self.socket = QtNetwork.QTcpSocket()
        self.socket.connected.connect(self.onConnected)
        self.socket.disconnected.connect(self.onDisconnected)
        self.socket.error.connect(self.onError)
        self.socket.stateChanged.connect(self.onStateChanged)
        self.socket.readyRead.connect(self.onReadyRead)

    def setClientName(self, name):
        self.client_name = name

    def onReadyRead(self):
        received_message = self.socket.readAll().data().decode()
        
        # logger.debug('Received message from connection %s: "%s"' % (socket_id, received_message.rstrip()))
        
        lines = received_message.split('\n')

        for line in lines:
            entries = line.split(':')
            if len(entries) > 1:
                if entries[0] == 'statechange':
                    input_terminal = entries[1]
                    new_state = entries[2]

                    self.setInputTerminalState(input_terminal, new_state)
                    
                else:
                    raise Exception


    def startClient(self):

        # Hmmmm.... Do the connecting in a thread instead...... 

        logger.debug('Connecting to host at %s, port %d' % (self.server_address, self.server_port))
        self.socket.connectToHost('127.0.0.1', 23456)
        self.socket.waitForConnected()


    def onConnected(self):
        logger.debug('Connected to host at %s, port %d' % (self.server_address, self.server_port))

        self.remoteRegisterClientName()
        self.remoteRegisterInputTerminals()
        self.remoteRegisterOutputTerminals()

       
    def onDisconnected(self):
        logger.debug('Disconnected from host at %s, port %d' % (self.server_address, self.server_port))
        # self.startClient()

        self.deRegisterOutputTerminals()
        self.deRegisterInputTerminals()


    def onError(self, error):
        logger.debug('Socket error occured: %s' % error)
        if error == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            self.startClient()


    def onStateChanged(self, state):
        logger.debug('Socket state changed to %s' % state)


    def registerInputTerminal(self, name, action=None):
        self.input_terminals[name] = {'name': name, 'state': self.no_state, 'action': action}


    def registerOutputTerminal(self, name, state=no_state):
        self.output_terminals[name] = {'name': name, 'state': state}


    def getOutputTerminalState(self, name):
        return self.output_terminals[name]['state']


    def setOutputTerminalState(self, name, new_state):
        if self.getOutputTerminalState(name) != new_state:
            self.output_terminals[name]['state'] = new_state
            self.remoteSendOutputTerminalState(name, new_state)


    def getInputTerminalState(self, name):
        return self.input_terminals[name]['state']


    def setInputTerminalState(self, name, new_state):
        if self.getInputTerminalState(name) != new_state:
            self.input_terminals[name]['state'] = new_state
            if self.input_terminals[name]['action']:
                self.input_terminals[name]['action'](new_state)


    def remoteRegisterClientName(self):
        message = 'clientname:' + self.client_name + '\n'
        self.socket.write(message.encode())
        logger.debug('Sent client name registration to server (%s).' % (self.client_name, ))


    def remoteRegisterInputTerminals(self):
        if len(self.input_terminals) > 0:
            message = 'registration:' + 'inputs:' + ':'.join(self.input_terminals) + '\n'
            self.socket.write(message.encode())
            logger.debug('Registered input terminals on server (%s).' % (', '.join(self.input_terminals)))


    def remoteRegisterOutputTerminals(self):
        if len(self.output_terminals) > 0:
            message = 'registration:' + 'outputs:' + ':'.join(self.output_terminals) + '\n'
            self.socket.write(message.encode())
            logger.debug('Registered output terminals on server (%s).' % (', '.join(self.output_terminals)))


    def remoteSendOutputTerminalState(self, terminal_name, new_state):
        message = 'statechange:' + ':'.join((terminal_name, new_state)) + '\n'
        self.socket.write(message.encode())
        logger.debug('Sent statechange on %s (new state: %s) to server' % (terminal_name, new_state))


    def deRegisterOutputTerminals(self):
        pass
        """NOOOOOOOOOOOOOO"""


    def deRegisterInputTerminals(self):
        pass
    



class SASConnectThread(QtCore.QThread):
    # Signals to relay thread progress to the main GUI thread
    progressSignal = QtCore.Signal(int)
    completeSignal = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(SASConnectThread, self).__init__(parent)
        # You can change variables defined here after initialization - but before calling start()
        #self.maxRange = 100
        #self.completionMessage = "done."

    def run(self):
        # blocking code goes here
        emitStep = int(self.maxRange/100.0) # how many iterations correspond to 1% on the progress bar

        for i in range(self.maxRange):
            #time.sleep(0.01)

            if i%emitStep==0:
                self.progressSignal.emit(i/emitStep)

        self.completeSignal.emit(self.completionMessage)