import time
import script

manager = script.SyncManager('home/ericdhiggins/Gantt-Manager/info.json')

while True:
    main_changed, resources_changed = manager.files_have_changed()
    if resources_changed or main_changed:
        print('Updating...')
        manager.sync_files(resources_changed)
    else:
        print('Nothing has changed.')
    time.sleep(20)
    
