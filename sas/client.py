
import logging

from PySide2 import QtCore, QtNetwork

logger = logging.getLogger(__name__)

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
        self.input_terminals[name] = {'name': name, 'state': 'None', 'action': action}


    def registerOutputTerminal(self, name):
        self.output_terminals[name] = {'name': name, 'state': 'None'}


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
    
