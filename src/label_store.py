from kivy_utils import get_storage_path
import os
import shutil



class LabelStore:
    """
    https://github.com/bitcoin/bips/blob/master/bip-0329.mediawiki
    """
    def __init__(self, app, wallet):
        self.kivyapp = app
        self.wallet = wallet
        self.loaded_initally = False
        self.name = 'BIP329-labels-{}.jsonl'.format(self.wallet.fingerprint)
        self._unsynced_labels = 0
        self._types = ['tx','input', 'output', 'addr', 'xpub', 'pubkey']
        self.store = []


    def _mark_synced(self):
        self._unsynced_labels = 0

    def check_for_import(self):
        if self.check_for_label_file():
            self.kivyapp.show_dialog("Import labels?", "Label file found")     

    def check_for_label_file(self, path=None):
        if path is None:
            path = get_storage_path(filename=self.name)
        if os.path.isfile(path):
            return True
        return False


    def load_from_file(self, path=None):
        if path is None:
            path = get_storage_path(filename=self.name)
        if os.path.isfile(path):
            print("BIP329 LOAD FROM FILE")
            self.loaded_initally = True


    def sync(self):
        self.save_to_file()
        self._mark_synced()



    def add_label(self, type, ref, label):
        print("{} {} {}".format(type, ref, label))
        self.store.append({"type": type, "ref":ref, "label": label})
        self._unsynced_labels += 1


    def save_to_file(self, path=None):
        """ Writes that file to the Downloads directly. """
        if path is None:
            path = get_storage_path(filename=self.name)
        if os.path.isfile(path) and self.loaded_initally:
            # Don't overwrite the file we imported initally.
            shutil.copyfile(path, "{}-backup-{}".foramt(path, self.kivyapp.block_height))
        f = open(path, "w")
        for entry in self.store:
            if all(item in list(entry.keys()) for item in ["ref", "label", "type"]):
                first = True
                line = "{"
                for k in entry.keys():
                    if line != "{":
                        line += ", "
                    line += "\"{}\": \"{}\"".format(k, entry[k])
                line += "}\n"
                f.write(line)
        f.close()
