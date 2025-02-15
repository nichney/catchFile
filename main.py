from pathlib import Path # to resolve path
import db #DataBase logic

def addDirectory():
    path = Path(input("Enter a directory path on your local device: ").strip()).resolve()
    
    dbm = db.DatabaseManager()
    for file in path.rglob('*'):
        if file.is_file():
            dbm.add_file(str(file))
            print(f"File {file} added to db")


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
    path = Path(input("Enter a directory path on your local device to remove it from sync: ").strip()).resolve()
    dbm = db.DatabaseManager()
    for file in path.rglob('*'):
        if file.is_file():
            dbm.unsync_file(str(file))
            print(f"File {file} uncynsed now")

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
