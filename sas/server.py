
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

    no_state = 'None'

    client_name_registered = QtCore.Signal(str)
    client_name_unregistered = QtCore.Signal(str)
    input_terminal_registered = QtCore.Signal(str, str, str)
    output_terminal_registered = QtCore.Signal(str, str, str, tuple)
    input_terminal_changed_state = QtCore.Signal(str, str, str)
    output_terminal_changed_state = QtCore.Signal(str, str, str)

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

    def getOutputConnections(self, output_terminal):
        if output_terminal in self.connections:
            return self.connections[output_terminal]
        else:
            return ()

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
        
        lines = received_message.split('\n')

        for line in lines:
            entries = line.split(':')
            if len(entries) > 1:
                if entries[0] == 'clientname':
                    client_name = entries[1]
                    self.registerClientName(client_name, socket_id)

                elif entries[0] == 'registration':
                    terminal_type = entries[1]
                    if terminal_type == 'inputs':
                        input_terminals = entries[2:]
                        self.registerInputTerminals(input_terminals, socket_id)
                    elif terminal_type == 'outputs':
                        output_terminals = entries[2:]
                        self.registerOutputTerminals(output_terminals, socket_id)

                elif entries[0] == 'statechange':
                    terminal_name = entries[1]
                    new_state = entries[2]
                    self.registerOutputTerminalStateChange(terminal_name, new_state)

                else:
                    raise Exception


    def registerClientName(self, name, socket_id):
        self.client_sockets[socket_id]['group'] = name
        self.client_name_registered.emit(name)
        logger.info('Client %s registered as %s.' % (socket_id, name))
    
    def registerInputTerminals(self, input_terminals, socket_id):
        for input_terminal_name in input_terminals:
            self.registered_input_terminal_states[input_terminal_name] = {'state': self.no_state, 'socket_id': socket_id}
            client_name = self.client_sockets[socket_id]['group']
            self.input_terminal_registered.emit(client_name, input_terminal_name, self.registered_input_terminal_states[input_terminal_name]['state'])
            logger.debug('Client %s registered an input terminal: %s)' % (socket_id, input_terminal_name))

            # Find all registered output terminals which are connected to terminal_name (should normally be only one), and get the 
            # initial state from there!
            connected_output_terminal_names = [output_terminal_name for output_terminal_name in self.registered_output_terminal_states if input_terminal_name in self.getOutputConnections(output_terminal_name)]
            assert len(connected_output_terminal_names) <= 1, 'Multiple output terminals connected to the same input terminal.'
            # This situation is quite allright if certain criterias is fulfilled, but for now we call this an abnormality and stops.

            # Now we send distribute the initial state back to the client.
            if len(connected_output_terminal_names) > 0:
                connected_output_terminal_name = connected_output_terminal_names[0]
                initial_state = self.registered_output_terminal_states[connected_output_terminal_name]['state']
                self.remoteSendInputTerminalState(input_terminal_name, initial_state)

    def registerOutputTerminals(self, output_terminals, socket_id):
        for terminal_name in output_terminals:
            self.registered_output_terminal_states[terminal_name] = {'state': self.no_state, 'socket_id': socket_id}
            
            client_name = self.client_sockets[socket_id]['group']
            self.output_terminal_registered.emit(client_name, terminal_name, self.registered_output_terminal_states[terminal_name]['state'], self.getOutputConnections(terminal_name))
            
            logger.debug('Client %s registered an output terminal: %s)' % (socket_id, terminal_name))


    def registerOutputTerminalStateChange(self, terminal_name, new_state):
        old_state = self.registered_output_terminal_states[terminal_name]['state']

        
        self.registered_output_terminal_states[terminal_name]['state'] = new_state
        
        socket_id = self.registered_output_terminal_states[terminal_name]['socket_id']
        client_name = self.client_sockets[socket_id]['group']
        self.output_terminal_changed_state.emit(client_name, terminal_name, new_state)

        logger.debug('%s changed state from %s to %s' % (terminal_name, old_state, new_state))

        if terminal_name in self.connections:
            for affected_input_terminal in self.connections[terminal_name]:
                self.remoteSendInputTerminalState(affected_input_terminal, new_state)

    def unRegisterTerminals(self, socket_id):
        socket_id_registered_out_terminals = [out_terminal for out_terminal in self.registered_output_terminal_states if self.registered_output_terminal_states[out_terminal]['socket_id'] == socket_id]
        socket_id_registered_in_terminals = [in_terminal for in_terminal in self.registered_input_terminal_states if self.registered_input_terminal_states[in_terminal]['socket_id'] == socket_id]

        for input_terminal in socket_id_registered_in_terminals:
            del self.registered_input_terminal_states[input_terminal]
            logger.debug('Deregistered input terminal %s' % (input_terminal, ))

        for output_terminal in socket_id_registered_out_terminals:
            self.registerOutputTerminalStateChange(output_terminal, self.no_state)

        for output_terminal in socket_id_registered_out_terminals:
            del self.registered_output_terminal_states[output_terminal]
            logger.debug('Deregistered input terminal %s' % (output_terminal, ))

        client_name = self.client_sockets[socket_id]['group']
        self.client_name_unregistered.emit(client_name)




    def remoteSendInputTerminalState(self, input_terminal_name, new_state):
        if input_terminal_name in self.registered_input_terminal_states:
            socket_id = self.registered_input_terminal_states[input_terminal_name]['socket_id']
            client_socket = self.client_sockets[socket_id]['socket']
            message = 'statechange:' + input_terminal_name + ':' + new_state + '\n'
            client_socket.write(message.encode())
            logger.debug('Sent statechange on %s (new state: %s) to %s' % (input_terminal_name, new_state, socket_id))

            socket_id = self.registered_input_terminal_states[input_terminal_name]['socket_id']
            client_name = self.client_sockets[socket_id]['group']
            self.input_terminal_changed_state.emit(client_name, input_terminal_name, new_state)


    def getClientSocketId(self, input_terminal_name):
        return self.registered_input_terminal_states[input_terminal_name]['socket_id']


    def closeSocket(self, socket_id):
        self.client_sockets[socket_id]['socket'].abort()
        self.unRegisterTerminals(socket_id)
        del self.client_sockets[socket_id]
        logger.debug('Connection %s closed' % socket_id)


class SASServer2(QtNetwork.QTcpServer):

    no_state = 'None'

    client_name_registered = QtCore.Signal(str)
    client_name_unregistered = QtCore.Signal(str)
    terminal_registered = QtCore.Signal(str, str, str, tuple)
    terminal_unregistered = QtCore.Signal(str)
    terminal_changed_state = QtCore.Signal(str, str, str)
    

    def __init__(self, server_port, connections_path, parent=None):
        super(SASServer2, self).__init__(parent)

        self.connections = {}

        self.buildTerminalConnections(connections_path)

        self.server_port = server_port

        self.client_sockets = {}
        
        self.registered_terminals = {}

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

        valid_entry_counter = 0
        connection_counter = 0

        for entry in entries:
            if entry.strip() and not entry.lstrip()[0] == '#':

                if len(entry.split('->')) != 2:
                    logger.warning('Malformed line in %s:\nLine: %s')
                else:
                    # No error check is done here!!!!!!!!
                    s1, s2 = entry.split('->')
                    
                    input_terminal = s1.strip()
                    
                    output_terminals = []
                    s2s = s2.split(',')
                    for each in s2s:
                        output_terminals.append(each.strip())

                    if input_terminal in self.connections:
                        self.connections[input_terminal].extend(output_terminals)
                    else:
                        self.connections[input_terminal] = output_terminals

                    for output_terminal in output_terminals:
                        if output_terminal in self.connections:
                            self.connections[output_terminal].append(input_terminal)
                        else:
                            self.connections[output_terminal] = [input_terminal]

                    connection_counter += len(output_terminals)
                    valid_entry_counter += 1
        
        logger.info('Successfully registered %d connections from %d entries.' % (connection_counter, valid_entry_counter))


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

        self.client_sockets[rand_id] = {'socket': new_socket, 'name': ''}

        logger.debug('New incoming connention: %s' % rand_id)


    def readSocket(self, socket_id):
        ready_socket = self.client_sockets[socket_id]['socket']
        
        received_message = ready_socket.readAll().data().decode()
        
        lines = received_message.split('\n')

        for line in lines:
            entries = line.split(':')
            if len(entries) > 1:
                if entries[0] == 'clientname':
                    client_name = entries[1]
                    self.registerClientName(client_name, socket_id)

                elif entries[0] == 'registration':
                    terminals = entries[1:]
                    self.registerTerminals(terminals, socket_id)

                elif entries[0] == 'statechange':
                    terminal_name = entries[1]
                    new_state = entries[2]
                    self.registerTerminalStateChange(terminal_name, new_state, socket_id)

                else:
                    raise Exception


    def registerClientName(self, client_name, socket_id):
        self.client_sockets[socket_id]['name'] = client_name
        self.client_name_registered.emit(client_name)
        logger.info('Client with id %s registered as %s.' % (socket_id, client_name))
    


    def registerTerminals(self, terminals, socket_id):
        for terminal_name in terminals:
            self.registered_terminals[terminal_name] = {'state': self.no_state, 'socket_id': socket_id}

            # Get all connected terminals here, and add them as a tuple to the emit below!
            if terminal_name in self.connections:
                connected_terminal_names = tuple(self.connections[terminal_name])
            else:
                connected_terminal_names = ()

            client_name = self.client_sockets[socket_id]['name']
            self.terminal_registered.emit(client_name, terminal_name, self.registered_terminals[terminal_name]['state'], connected_terminal_names)
            logger.debug('Client %s registered a terminal: %s)' % (client_name, terminal_name))

            # Hmmm.... Set state according to connected terminals here????? No, all logic at client side!


    def registerTerminalStateChange(self, terminal_name, new_state, socket_id):

        assert terminal_name in self.registered_terminals, 'Tried to register a statechange on %s, but this terminal is not registered at the server.' % terminal_name

        old_state = self.registered_terminals[terminal_name]['state']

        # Set new state
        self.registered_terminals[terminal_name]['state'] = new_state

        client_name = self.client_sockets[socket_id]['name']

        self.terminal_changed_state.emit(client_name, terminal_name, new_state)

        logger.debug('%s changed state from %s to %s' % (terminal_name, old_state, new_state))

        # Send new state to all connected terminals. Further actions will be taken care of at
        # the client side.
        if terminal_name in self.connections:
            for connected_terminal in self.connections[terminal_name]:
                self.remoteSendTerminalState(connected_terminal, new_state)


    def unRegisterTerminals(self, socket_id):
        socket_id_registered_terminals = [terminal for terminal in self.registered_terminals if self.registered_terminals[terminal]['socket_id'] == socket_id]

        for terminal_name in socket_id_registered_terminals:
            self.registerTerminalStateChange(terminal_name, self.no_state, socket_id)

        for terminal_name in socket_id_registered_terminals:
            del self.registered_terminals[terminal_name]
            logger.debug('Unregistered terminal %s' % (terminal_name, ))

        client_name = self.client_sockets[socket_id]['name']
        self.client_name_unregistered.emit(client_name)


    def remoteSendTerminalState(self, terminal_name, new_state):
        if terminal_name in self.registered_terminals:
            if self.getTerminalState(terminal_name) != new_state:
                socket_id = self.registered_terminals[terminal_name]['socket_id']
                client_socket = self.client_sockets[socket_id]['socket']
                client_name = self.client_sockets[socket_id]['name']
                message = 'statechange:' + terminal_name + ':' + new_state + '\n'
                client_socket.write(message.encode())
                logger.debug('Sent statechange on %s (new state: %s) to %s' % (terminal_name, new_state, client_name))

            # self.terminal_changed_state.emit(client_name, terminal_name, new_state)


    def getClientSocketId(self, terminal_name):
        return self.registered_input_terminal_states[terminal_name]['socket_id']

    def getTerminalState(self, terminal_name):
        return self.registered_terminals[terminal_name]['state']


    def closeSocket(self, socket_id):
        self.client_sockets[socket_id]['socket'].abort()
        self.unRegisterTerminals(socket_id)
        del self.client_sockets[socket_id]
        logger.debug('Connection %s closed' % socket_id)

