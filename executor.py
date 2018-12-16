import time
import script

manager = script.SyncManager('info.json')

while True:
    if manager.files_have_changed():
        print('Updating...')
        manager.sync_files()
    else:
        print('Nothing has changed.')
    time.sleep(20)
    