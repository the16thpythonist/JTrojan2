import multiprocessing as mp
import JTrojan2.communication as comm
import threading
import pickle
import codecs
import socket
import time


class SocketWrapper:

    def __init__(self, sock, connected):
        # Assigning the socket object to the variable
        self.sock = sock
        # The variable, which stores the state of the connection
        self.connected = connected
        # The properties, that describe the type of the socket
        self.family = None
        self.appoint_family()
        self.type = None
        self.appoint_type()

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
                self.sock = socket.socket(self.family, self.type)
                self.connected = False
                # Decrementing the counter for the attempts
                attempts -= 1

        # In case the loop exits without the connection being established
        if self.attempts == 0:
            raise ConnectionRefusedError("The socket could not connect to {}".format(address))

    def receive_until_character(self, character, limit, timeout=None, include=False):
        """
        This method receives data from the wrapped socket until the special 'character' has been received. The limit
        specifies after how many bytes without the termination character a Error should be raised. The timeout
        is the amount of seconds every individual byte is allowed to take to receive before raising an error. The
        include flag tells whether the termination character should be included in the returned data.
        Args:
            character: can either be an integer in the range between 0 and 255, that is being converted into a
                character or can be a bytes object/ bytes string of the length 1. After receiving this byte the data
                up to that point is returned.
            limit: The integer amount of bytes, that can be received without terminating, without raising an error.
            timeout: The float amount of seconds each individual byte is allowed to take to receive before a
                Timeout is raised.
            include: The boolean flag of whether to include the termination character in the return or not

        Returns:
        The data bytes, that were received up to the point, when the termination character was received
        """
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

    def sendall(self, data):
        """
        Simply wraps the 'sendall' method of the actual socket object.
        Raises:
            ConnectionError: In case the socket is not connected yet.
        Args:
            data: The data to be sent over the socket, best case would be bytes already, does not have to be though

        Returns:
        void
        """
        # Checking if the socket is already connected
        if not self.connected:
            raise ConnectionError("There is no open connection to send to yet!")
        # Actually calling the method of the socket
        self.sock.sedall(data)

    def release_socket(self):
        """
        This method releases the socket from the wrapper, by setting the internal property to the socket to None and
        returning the wrapper
        Returns:
        The socket, that was used by the wrapper
        """
        # Removing the pointer to the socket from the object property and returning the socket
        sock = self.sock
        self.sock = None
        return sock

    def appoint_family(self):
        """
        This method simply sets the family attribute of the object to the same value as the family property of the
        socket, that is being wrapped
        Returns:
        void
        """
        self.family = self.sock.family

    def appoint_type(self):
        """
        this method simply sets the type property of the object to the same value as the type property of the
        socket, that is being wrapped.
        Returns:
        void
        """
        self.type = self.sock.type


class Greeter(mp.Process):
    """
    The Greeter process is the first network instance of the trojan server system, its only job is to listen at the
    designated port of the local machine and accept all incoming connection and putting all the resulting bound
    sockets and their origin addresses as a tuple (in that order) into the multiprocessing queue, that was specified.
    Args:
        port: The integer port at which the server is supposed to listen
        output_queue: A multiprocessing.Queue, into which the accepted socket connections are being put
        state: A multiprocessing.Value of boolean type, by which the mother process of the server can control the main
            loop of the Greeter
        family: The family for the server socket. Basically the decision between using ip4 or ip6.
            Default on ip4
        ip: The string ip at which to listen to the incoming connections.
            Default on the local machine, by 'localhost'
    """
    def __init__(self, port, output_queue, state, family=socket.AF_INET, ip="localhost"):
        mp.Process.__init__(self)
        # The name of the process#
        self.name = "greeter"
        # The network information
        self.ip = ip
        self.port = port
        self.family = family
        # The output queue for the sockets
        self.output = output_queue

        # Creating the socket and binding it to the address
        self.sock = None
        self.init_socket()

        # The state is a shared variable amongst the Processes and controls their main loops, so they dont have to be
        # terminated by force and eventually corrupting the queues
        self.running = state

    def run(self):
        """
        This is the main method of the process, which runs the main loop. The greeter will constantly wait for new
        connections to come and will relay the resulting bound socket and the origin address to the output queue
        Returns:
        void
        """
        # Making the server start to listen
        self.sock.listen(10)

        try:
            while self.running is True:
                # Constantly accepting new connections and putting the socket and the address into the output queue
                connection, address = self.sock.accept()
                self.output.put((connection, address))
        except socket.error:
            pass
        finally:
            # Closing the socket in case of termination
            self.sock.close()

    def init_socket(self):
        """
        This method creates a new socket in the 'sock' property of the object and then configures it to be a listening
        server socket and binding it to the address, that was passed to the object on creation.
        Returns:
        void
        """
        # Creating a new socket
        self.create_socket()
        # Setting the socket to listen
        address = self.assemble_address()
        self.sock.bind(address)

    def create_socket(self):
        """
        This method creates a new raw socket in the 'sock' property, which also means closing the old one, in case
        there is one already there.
        Returns:
        void
        """
        # Closing the old socket in case there is one
        if self.sock is not None:
            try:
                self.sock.close()
            except socket.error:
                pass
        # Creating a new socket
        self.sock = socket.socket(self.family, socket.SOCK_STREAM)

    def assemble_address(self):
        """
        This method simply puts the ip and the port into a tuple to create the address, that sockets use
        Returns:
        A tuple with the first element being the ip string at which the server is supposed to listen and the second
        element being the integer port at which the server is supposed to listen.
        """
        return self.ip, self.port


class FormReceiveHandler(threading.Thread):

    def __init__(self, output_queue):
        threading.Thread.__init__(self)
        # Putting the already connected socket into the wrapper fro easier handle
        self.sock = None
        self.sock_wrap = None
        # The queue into which the finished form and socket are supposed to be put into
        self.output = output_queue

        self.running = False
        # The idle flag tells the manager, if the handler can be used again or if it is still working
        self.idle = True

        # The dictionary that saves the data in every step
        self.data = {}
        self.form = None

    def run(self):
        """
        The main method of the Thread. As long as the Thread is running the loop will wait until it is assigned a new
        socket. It will then start to receive the data from the socket line by line and add each line, which consits of
        a identifier and the content, as a key-value-pair into a dict. When all the data has been received the dict
        will be converted into the according communication form and will then, together with the socket itself, be
        put into the output queue. Then the loop starts to wait for a new socket to handle.
        Returns:
        void
        """
        # Updating the running flag to True
        self.running = True

        while self.running:
            # Waiting for a new socket to be assigned to handle
            while self.idle is True:
                time.sleep(0.0001)

            # Creating the dictionary for the data received. Clearing it, if this is 2nd+ run of handler
            self.data = {}

            # Receiving the header, and adding it as a normal string to the dictionary
            header = self.receive_header()
            self.evaluate_header(header)

            identifier = b''

            # Receiving all the lines until one is the length line, indicating that the following is encoded content or
            # it is the end line
            while identifier != b'end':
                identifier, content = self.receive_content_line()
                self.evaluate_content(identifier, content)
                # In case the identifier is the length, receiving the next line as encoded line
                if identifier == b'length':
                    # Turning the length content into a int, so that it can be used to know how many bytes too receive
                    length = int(self.create_content_string(content))
                    # Getting the encoded data from the socket and adding it to the dictionary after decoding it
                    identifier, content = self.receive_encoded_line(length)
                    self.evaluate_encoded_content(identifier, content)

            # After all the data is received, which means the data dict contains all the lines of the form, the data
            # dict is being turned into a form
            self.form = comm.produce_form(self.data)
            output = self.assemble_output()
            self.output.put(output)
            # Releasing the socket
            self.sock = None

    def assign(self, sock):
        """
        this method will be used by whatever higher instance will manage the handler to assign it a new job. More
        specifically assigning it a new socket to begin receiving the form from
        Args:
            sock: The socket object, that should be handled

        Returns:
        void
        """
        # Assigning the socket to the property and creating the socket wrapper
        self.sock = sock
        self.create_socket_wrap()
        # Resetting the idle property so that the main loop exits
        self.idle = False

    def assemble_output(self):
        """
        This method simply assembles the socket object and the form object into a tuple, that can be passed through the
        output queue
        Returns:
        The tuple, whose first element is the socket used for the transmission and the second the received form
        """
        assert self.form is not None
        return self.sock, self.form

    def receive_encoded_line(self, length):
        """
        This method receives a line of encoded data from the socket, if given the length of the data in bytes.
        Args:
            length: The integer length of the data in the encoded line. Only the content! identifier does not count

        Returns:
        A tuple, whose first element is the byte string of the identifier and the second item being the actual content
        in byte strings.
        """
        assert isinstance(self.sock_wrap, SocketWrapper)
        # First receiving the identifier from the next line, so until the ':'
        identifier = self.sock_wrap.receive_until_character(b':')
        # Now receiving as many bytes as specified
        content = self.sock_wrap.receive_length(length)
        self.sock_wrap.receive_length(1)
        return identifier, content

    def receive_content_line(self):
        """
        This method receives a single line from the socket and then splits it into the identifier, which tells about
        what information the line actually is, and the actual content.
        Returns:
        A tuple, whose first element is the byte string of the identifier and the second item being the byte string
        of the content
        """
        byte_string = self.receive_line()
        # Splitting the line into the identifier and the content
        split_list = byte_string.split(b':')
        # Returning the tuple of the identifier byte string and the content byte string
        return tuple(split_list)

    def receive_header(self):
        """
        This method will receive one line from the socket and save it into the data dictionary with the key as header,
        thus the method should only be called first, when beginning to receive the data.
        The name and the key will be saved as byte strings
        Returns:
        void
        """
        byte_string = self.receive_line()
        return byte_string

    def receive_line(self):
        """
        This method will receive data from the socket until a line break character is being received, so essentially
        receives one line from the socket.
        Returns:
        The received byte string without the newline character
        """
        byte_string = self.sock_wrap.receive_until_character(b'\n', 500)
        return byte_string

    def create_socket_wrap(self):
        """
        This method creates a SocketWrapper object and assigns it to the 'sock_wrap' property
        Returns:
        void
        """
        self.sock_wrap = SocketWrapper(self.sock, True)

    def add_header(self, header):
        """
        Simply adds the header string to the internal dictionary
        Args:
            header: The string (not byte string!) of the header to add to the dict

        Returns:
        void
        """
        self.data["header"] = header

    def evaluate_header(self, header):
        # Turning the byte string into a string and then adding it to the dict
        header = self.create_content_string(header)
        self.add_header(header)

    def evaluate_content(self, identifier, content):
        """
        This method takes the byte string identifier and content of a line received by the socket and turns the
        identifier into a string and evaluates the type of the content, turning it into either a int, a string or
        a list of strings.
        The type converted content is then used as the value to the identifier as key in the internal data dictionary
        Args:
            identifier: The byte string identifier for the content in a line
            content: The byte string of the content

        Returns:
        void
        """
        # Turning the byte string identifier into a string
        identifier = self.create_content_string(identifier)
        # If the content contains a comma or more, it is interpreted as a list of individual strings
        if b',' in content:
            self.data[identifier] = self.create_content_list(content)
        else:
            # First creating the correct string representation of the byte string
            string_content = self.create_content_string(content)
            # Attempting to turn the string into a integer. But setting the string directly as the dictionary item in
            # case the string did not represent a integer.
            try:
                self.data[identifier] = int(string_content)
            except ValueError:
                self.data[identifier] = string_content

    def evaluate_encoded_content(self, identifier, content):
        """
        This method takes the bytes string of the identifier of a data line, that is supposed to represent a complex
        data type and is thus encoded and pickled. The method will turn the identifier into string and convert the
        content back into its original data type and then add it as key; value pair to the internal data dict.
        Args:
            identifier: The bytes string of the identifier
            content: The bytes string of the encoded data object

        Returns:
        void
        """
        # Turning the identifier into a string
        identifier = str(identifier)
        # Decoding and unpicking the content
        content = self.create_content_decoded(content)
        # Adding them to the dictionary
        self.data[identifier] = content

    @staticmethod
    def create_content_string(content):
        """
        This method will take the content of a line received by the socket and turn the bytes object into a string
        Args:
            content: The bytes object, that was received as the content too one line of the form

        Returns:
        The string to the bytes string
        """
        # Turning the bytes object into a string first and then stripping the additional '' characters
        content_string = str(content)
        content_string = content_string[2:][:-1]
        return content_string

    @staticmethod
    def create_content_list(content):
        """
        This method will take the content line, that was received from the socket ans interprets it as comma separated
        list of individual string values
        Args:
            content: The bytes object, that was received as the content to one line of the form

        Returns:
        The list of strings
        """
        # Turning into a string
        content_string = str(content)
        # Splitting the string by the comma
        content_list = content_string.split(",")
        return content_list

    @staticmethod
    def create_content_decoded(content):
        """
        This method will take the content of a line, that was received from the socket and interpret it as encoded
        and pickled data and thus will decode it using the 'base64' codec and then unpickle the resulting bytes object
        Args:
            content: The bytes string, that was received as content to a line of the form

        Returns:
        The object that was originally pickled
        """
        # Decoding the content byte string
        content_bytes = codecs.decode(content.encode(), "base64")
        # Unpickling the data
        content_object = pickle.loads(content_bytes)
        # Returning the unpickled object
        return content_object


class Evaluator(mp.Process):

    def __init__(self, input_queue, output_queue, state, handler_amount=2):
        mp.Process.__init__(self)
        # The queues working as standardized interfaces
        self.input = input_queue
        self.output = output_queue

        self.running = state

        self.handler_amount = handler_amount
        self.handlers = []

    def run(self):

        while self.running is True:
            pass

    def add_handler(self):
        """
        This method will create a new FormReceiveHandler, start the Thread and add it to the internal list
        Returns:
        void
        """
        handler = FormReceiveHandler(self.output)
        handler.start()
        self.handlers.append(handler)




