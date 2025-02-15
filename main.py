def addDirectory():
    # Add directory to syncing.
    # TODO: dialogue to get directory path and write it to database
    path = input("Enter a directory path on your local device: ").strip()
    # TODO: check correctness

def addDevice():
    # TODO: generate a magnet link
    pass

def connect2device():
    # TODO: connect by magnet link from other device
    pass

def removeDirectory():
    # TODO: stop syncing existing directory, but do not delete it
    pass

def removeFiles():
    # TODO: mark files in database as deleted
    # an idea is to give a special mark in database for deleting file, and other devices, if they get that mark, 
    # delete such file, but do not delete database entry
    pass

if __name__ == '__main__':
    while True:
        print('Welcome to CatchFile 0.1a, an opensource tool for synchronizing'
           'files on all your devices. Here\'s menu:\n'
           '[ 1 ] - add directory\n[ 2 ] - add device\n[ 3 ] - connect\n[ 4 ]'
           ' - remove directory from sync\n[ 5 ] - remove files on synced devices')
        try:
            ans = int(input())
        except ValueError:
            print("Invalid input! Please, enter a number from menu.")
            continue
        match ans:
            case 1:
                addDirectory()
            case 2:
                addDevice()
            case 3:
                connect2device()
            case 4:
                removeDirectory()
            case 5:
                removeFiles()
            case _:
                print('Invalid choice! Please, select a valid option.')
