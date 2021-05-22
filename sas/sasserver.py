
import random
import string
import logging

from PySide2 import QtCore, QtNetwork

logger = logging.getLogger(__name__)

# logger.info('%s' % str)   
# logger.warning('%s' % str)
# logger.error('%s' % str)
# logger.critical('%s' % str)   
# logger.debug('%s' % str)

class SASClientSocket(QtNetwork.QTcpSocket):

    readyReadId = QtCore.Signal((str,))
    disconnectedId = QtCore.Signal((str,))

    def __init__(self, id, parent):
        super(SASClientSocket, self).__init__(parent)
        """
        The 'readyRead' signal is from QTcpSocket, call 'readyReadId' 
        whenever is emitted.
        """
        self.id = id
        
        self.readyRead.connect(self.onReadyRead)
        self.disconnected.connect(self.onDisconnected)

    def onReadyRead(self):
        """
        Re-emits a ready signal that sends the ID, so the Server knows
        which socket is ready.
        """
        self.readyReadId.emit(self.id)

    def onDisconnected(self):
        """
        Re-emits a ready signal that tells the server that the client
        closed the socket.
        """
        self.disconnectedId.emit(self.id)


class SASServer(QtNetwork.QTcpServer):

    def __init__(self, server_port, connections_path, parent=None):
        super(SASServer, self).__init__(parent)

        self.connections = {}

        self.buildTerminalConnections(connections_path)

        self.server_port = server_port

        self.client_sockets = {}
        self.registered_input_terminal_states = {}
        self.registered_output_terminal_states = {}

        # Starts listening on selected port.
        started = self.listen(address = QtNetwork.QHostAddress.Any, port = self.server_port)

        if started:
            logger.info('Server now listening on port %d' % self.server_port)
        else:
            logger.critical('Server could not bind to port %d' % self.server_port)


    def buildTerminalConnections(self, connections_path):
        try:
            f = open(connections_path, 'r')
        except FileNotFoundError:
            logger.critical('%s does not exist. No connections registered.' % connections_path)
            return

        entries = f.readlines()

        counter = 0

        for entry in entries:
            if entry.strip() and not entry.lstrip()[0] == '#':

                if len(entry.split('->')) != 2:
                    logger.warning('Malformed line in %s:\nLine: %s')
                else:
                    # No error check is done here!!!!!!!!
                    s1, s2 = entry.split('->')
                    
                    output_terminal = s1.strip()
                    
                    input_terminals = []
                    s2s = s2.split(',')
                    for each in s2s:
                        input_terminals.append(each.strip())

                    self.connections[output_terminal] = tuple(input_terminals)

                    counter += 1
        
        logger.info('Successfully registered %d connections.' % counter)


    def quit(self):
        pass


    def incomingConnection(self, socketDescriptor):
        # Generates a random string in order to tell sockets apart, and make sure it's unique.
        rand_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(3))
        while rand_id in self.client_sockets.keys():
            rand_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(3))

        new_socket = SASClientSocket(rand_id, parent=self)
        new_socket.setSocketDescriptor(socketDescriptor)
        new_socket.readyReadId.connect(self.readSocket)
        new_socket.disconnectedId.connect(self.closeSocket)

        self.client_sockets[rand_id] = {'socket': new_socket}

        logger.debug('New incoming connention: %s' % rand_id)


    def readSocket(self, socket_id):
        ready_socket = self.client_sockets[socket_id]['socket']
        
        received_message = ready_socket.readAll().data().decode()
        
        # logger.debug('Received message from connection %s: "%s"' % (socket_id, received_message.rstrip()))
        
        lines = received_message.split('\n')

        for line in lines:
            entries = line.split(':')
            if len(entries) > 1:
                if entries[0] == 'clientname':
                    self.registerClientName(entries[1:], socket_id)
                elif entries[0] == 'registration':
                    self.registerTerminals(entries[1:], socket_id)
                elif entries[0] == 'statechange':
                    self.registerOutputTerminalStateChange(entries[1:])
                else:
                    raise Exception


    def registerClientName(self, entries, socket_id):
        client_name = entries[0]
        self.client_sockets[socket_id]['group'] = client_name


    def registerOutputTerminalStateChange(self, entries):
        output_terminal_name = entries[0]
        new_state = entries[1]
        old_state = self.registered_output_terminal_states[output_terminal_name]['state']
        self.registered_output_terminal_states[output_terminal_name]['state'] = new_state
        logger.debug('Received statechange on %s (old state: %s, new_state: %s)' % (output_terminal_name, old_state, new_state))

        if output_terminal_name in self.connections:
            for affected_input_terminal in self.connections[output_terminal_name]:
                self.remoteSendInputTerminalState(affected_input_terminal, new_state)


    def remoteSendInputTerminalState(self, input_terminal_name, new_state):
        socket_id = self.registered_input_terminal_states[input_terminal_name]['socket_id']
        client_socket = self.client_sockets[socket_id]['socket']
        message = 'statechange:' + input_terminal_name + ':' + new_state + '\n'
        client_socket.write(message.encode())
        logger.debug('Sent statechange on %s (new state: %s) to %s' % (input_terminal_name, new_state, socket_id))


    def getClientSocketId(self, input_terminal_name):
        return self.registered_input_terminal_states[input_terminal_name]['socket_id']


    def registerTerminals(self, entries, socket_id):
        client_name = entries[0]
        terminal_type = entries[1]

        for terminal_name in entries[2:]:
            if terminal_type == 'inputs':
                self.registered_input_terminal_states[terminal_name] = {'group': client_name, 'state': 'None', 'socket_id': socket_id}
                logger.debug('Registered input terminal: %s (group=%s, state=None, socket_id=%s)' % (terminal_name, client_name, socket_id))
            elif terminal_type == 'outputs':
                self.registered_output_terminal_states[terminal_name] = {'group': client_name, 'state': 'None', 'socket_id': socket_id}
                logger.debug('Registered output terminal: %s (group=%s, state=None, socket_id=%s)' % (terminal_name, client_name, socket_id))
            else:
                logger.critical('Some error in registration message.')
                raise Exception

    
    def closeSocket(self, socket_id):
        logger.debug('Connection %s closed.' % socket_id)
        self.client_sockets[socket_id]['socket'].abort()
        # del self.client_sockets[socket_id]

