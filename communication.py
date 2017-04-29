import codecs
import pickle


class RequestForm:
    """
    This class represents the string, that is being sent from the user of the JTrojan system to the server. The request
    transmission is according to a form, that begins with the request header and which specifies the following
    information:
    - id: The id of the user, that sends the request, so that the server can address the response to the correct socket
    - function name: The name of the function to be executed within the server
    - return mode: whether or not the server is supposed to return the resulting data immediatly or store it in the
        buffer if the users profile. So whether the user is executing as blocking or non blocking command
    - error mode: -
    - addresses: A list with the entities, that are being addresses by the function, so on which trojans the function
        is supposed to be executed on
    - parameters: The parameters of the function call. Originally given as a list and then pickled and string encoded
    """

    header = "REQUEST"

    def __init__(self, function_name, parameters, addresses, return_mode, error_mode, id):
        self.function_name = function_name
        self.parameters = parameters
        self.addresses = addresses
        self.return_mode = return_mode
        self.error_mode = error_mode
        self.id = id

        # The length of the parameters byte object as it is being received
        self._length = None

    def create_form_string(self):
        """
        This method creates the string for the whole form in general. The form consists of the Header, that identifies
        the type of message that is being sent and the lines with the identifiers separated by ':' to the values.
        The lines are separated by \n except for the last line which is variable in length. The length is specified.
        Returns:
        The string of the form string
        """
        string_list = [self.header]
        # Adding the id of the user
        id_string = self.create_id_string()
        string_list.append(id_string)
        # Adding function name line
        function_name_string = self.create_function_name_string()
        string_list.append(function_name_string)
        # Adding return handle line
        return_mode_string = self.create_return_mode_string()
        string_list.append(return_mode_string)
        # Adding the error mode line
        error_mode_string = self.create_error_mode_string()
        string_list.append(error_mode_string)
        # Adding the addresses string
        addresses_string = self.create_addresses_string()
        string_list.append(addresses_string)
        # Creating the parameters string first and then the length line, adding the length line first.
        # The parameters have to be created first, because the method calculates the length first
        parameters_string = self.create_parameter_string()
        length_string = self.create_length_string()
        string_list.append(length_string)
        string_list.append(parameters_string)
        # Actually assembling the string from the list
        return '\n'.join(string_list)

    def create_length_string(self):
        """
        This method creates the string for the length. The length is an integer value and specifies how many bytes have
        to be read for the encoded parameters line, after the identifier !
        Returns:
        The string line
        """
        # The length property has to be set for the length line to be created
        assert self._length is not None
        # The string list, that will be the string
        string_list = ["length:", str(self._length)]
        return ''.join(string_list)

    def create_id_string(self):
        """
        This method creates the string line, that tells the server which user has sent the request, so that it can send
        the return of the request to the correct user
        Returns:
        The string line
        """
        string_list = ["id:", str(self.id)]
        return ''.join(string_list)

    def create_function_name_string(self):
        """
        This function creates the line, that specifies the function name, that is used to call the accorcing function
        within the server. The line consists of the 'function:' identifier and the actual function name string, that
        was passed to the Template object for creation
        Returns:
        The string line (without a newline character)
        """
        # Creating the string for the line in which the function name is being specified
        string_list = ["function:", str(self.function_name)]
        # returning the assembled string
        return ''.join(string_list)

    def create_return_mode_string(self):
        """
        this function creates the string line, that is used to tell the server, which type of return behaviour is
        expected. The main return behaviours are to directly return the data or to sjust store it in the user profile
        buffer of the server for later recall (blocking and non blocking)
        Returns:
        The string line(without the new line character)
        """
        # Creating the string, that specifies the return mode to be used in the servers execute system
        string_list = ["return:", str(self.return_mode)]
        # Returning the assembled string
        return ''.join(string_list)

    def create_error_mode_string(self):
        """
        This method creates the string line, that specifies the expected error behaviour for the server.
        Returns:
        The string line
        """
        string_list = ["error:", str(self.error_mode)]
        # Returning the assembled string
        return ''.join(string_list)

    def create_addresses_string(self):
        """
        This method creates the line of the form, that specifies which entities are being addressed by the function
        call. A single command can be issued to just one trojan, all, just a few or the server etc.
        Returns:
        The string line
        """
        string_list = ["addresses:"]
        # Encoding the list of the entities, that the user addresses with the request as comma separated strings
        for address in self.addresses:
            address_string = str(address)
            # Adding the address and a comma
            string_list.append(address_string)
            string_list.append(",")
        # Removing the last item of the list, which is a comma in every case
        string_list.pop()
        # Returning the assembled string
        return ''.join(string_list)

    def create_parameter_string(self):
        """
        This method creates the string line for the parameters of the function call. The parameters are given as a list
        of objects and is transferred in a pickled state. The pickled data is additionally encoded with the 'bas64'
        code of the codecs module to fit as a actual string.
        This method also updates the length property, thus enabling the creation of the length string.
        Notes:
            Due to the encoding, the line of the parameters cannot simply by terminated by a special character, thats
            why a additional length attribute is part of the template, that specifies how long the parameter data is to
            read that from the the socket. termination by fixed length
        Returns:
        the string line for the parameter(without newline character9
        """
        string_list = ["parameters:"]
        # Pickling the parameters object into a bytes object
        pickled_parameters = pickle.dumps(self.parameters)
        # Encoding the pickled data into a byte string of the 'base64' encoding and then into an actual string
        encoded_byte_string = codecs.encode(pickled_parameters, "base64")
        self._length = len(encoded_byte_string)
        encoded_string = str(encoded_byte_string)[2:][:-1]
        # Adding to the string list to convert the final assembled string
        string_list.append(encoded_string)
        return ''.join(string_list)


if __name__ == '__main__':
    f = RequestForm("get", ["hallo", True], ["max", "anna"], "blocking", "discard", "Jonas")
    print(f.create_form_string())


