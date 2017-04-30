import socket
import time


class SocketWrapper:

    def __init__(self, sock, connected):
        # Assigning the socket object to the variable
        self.sock = sock
        # The variable, which stores the state of the connection
        self.connected = connected

    def connect(self, ip, port, attempts, delay):
        """
        This method capsules the connect functionality of the wrapped socket. The method will try to connect to the
        specified address, trying that the specified amount of attempts.
        In case an already connected socket is already stored in the wrapper, this method will close and connect to the
        new address (in case that is possible obviously).
        In case the connection could not be established after the specified amount of attempts, the method will raise
        an ConnectionRefusedError!
        Args:
            ip: The string ip address of the target to connect to
            port: The integer port of the target to connect to
            attempts: The integer amount of attempts of trying to connect
            delay: The float amount of seconds delayed to the next attempt

        Returns:
        void
        """
        # Checking the data types for the inputs
        assert isinstance(ip, str), "ip is not a string"
        assert isinstance(port, int) and (0 <= port <= 65536), "The port is wrong type or value range"
        assert isinstance(attempts, int) and (0 <= attempts), "The attempts parameter is not the same value"
        # Saving the type and the family of the socket, so that a new one can be created in case the other is corrupted
        socket_family = self.sock.family
        socket_type = self.sock.type
        # Assembling the port and the ip to the address tuple
        address = (ip, port)
        # Calling the connect of the socket as many times as specified
        while not self.connected:
            try:
                # Delaying the try possibly
                time.sleep(delay)
                # Attempting to build the connection
                self.sock.connect(address)
                # Updating the connected status to True
                self.connected = True
            except Exception as exception:
                # Closing the socket and creating a new one, which is gonna be used in the next try
                self.sock.close()
                self.sock = socket.socket(socket_family, socket_type)
                self.connected = False
                # Decrementing the counter for the attempts
                attempts -= 1

        # In case the loop exits without the connection being established
        if self.attempts == 0:
            raise ConnectionRefusedError("The socket could not connect to {}".format(address))

    def receive_until_character(self, character, limit, timeout=None, include=False)
        # Checking for the data type fo
        is_bytes = isinstance(character, bytes)
        is_int = isinstance(character, int)
        assert (is_bytes and len(character) == 1) or (is_int and 0 <= character <= 255)
        # In case the input is an integer converting it into a bytes object
        if is_int:
            character = int.to_bytes(character, "1", "big")

        counter = 0
        # Calling the receive length function with one byte at a time until the character in question appears
        data = b""
        while True:
            # Checking if the limit of bytes has been reched
            if counter > limit:
                raise OverflowError("The limit of bytes to receive until character has been reached")
            current = self.receive_length(1, timeout)
            if current == character:
                if include is True:
                    data += character
                # After the character has been found and eventually was added to the data, breaking the infinite loop
                break
            else:
                # In case the character is not there adding the byte to the counter and incrementing the counter
                data += character
                counter += 1

        return data


    def receive_length(self, length, timeout=None):
        """
        This method receives a certain amount of bytes from the socket object, that is being wrapped. It is also
        possible to specify the amount of time the method is supposed to wait for the next character to be received
        before issuing a timeout.
        Raises:
            EOFError: In case the data stream terminated before the specified amount of bytes was received
            ConnectionError: In case the socket object in question is not connected yet.
            TimeoutError: In case it took to long to receive the next byte
        Args:
            length: The integer amount of bytes to be received from the socket
            timeout: The float amount of time, that is tolerated for a byte to be received

        Returns:
        The bytes string of the data with the specified length, received from the socket
        """
        # First checking whether or not there actually is a callable socket within the 'connection' attribute, by
        # checking the 'connected' flag. In case there is not, will raise an exception
        if not self.connected:
            raise ConnectionError("There is no open connection to receive from yet!")

        start_time = time.time()
        data = b''
        while len(data) < length:
            # receiving more data, while being careful not accidentally receiving too much
            more = self.sock.recv(length - len(data))

            # In case there can be no more data received, but the amount of data already received does not match the
            # amount of data that was specified for the method, raising End of file error
            if not more:
                raise EOFError("Only received ({}/{}) bytes".format(len(data), length))

            # Checking for overall timeout
            time_delta = time.time() - start_time
            if (timeout is not None) and time_delta >= timeout:
                raise TimeoutError("{} Bytes could not be received in {} seconds".format(length, timeout))

            # Adding the newly received data to the stream of already received data
            data += more
        return data
