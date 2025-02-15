from pathlib import Path # to resolve path
import os
import db #DataBase logic
import link_resolver # for magnet links

def addDirectory():
    path = Path(input("Enter a directory path on your local device: ").strip()).resolve()
    
    dbm = db.DatabaseManager()
    for file in path.rglob('*'):
        if file.is_file():
            dbm.add_file(str(file))
            print(f"File {file} added to db")


def addDevice():
    key = os.urandom(32) 
    generator = link_resolver.MagnetLinkGenerator()
    magnet_link = generator.generate_magnet_link(key)

    print("Magnet-link:", magnet_link)
    print("This link contains encryption key and should be shared securely.")

def connect2device():
    magnet_link = input("Enter link to connect device: ").strip()

    try:
        link_data, key = link_resolver.MagnetLinkGenerator.decode_link(magnet_link)
        shared_db_hash = link_data['db_hash']

        print(f'Connected to device! Shared DB hash: {shared_db_hash}')
        print(f'Encryption key (store securely!): {key.hex()}')

        dbm = db.DatabaseManager()
        missing_files = dbm.get_missing_files()
        if missing_files:
            print('Requesting missing files...')
            for file_hash in missing_files:
                print(f'Need file {file_hash}')
                # TODO: download missing files
        else:
            print('All files are up to date')
    except Exception as e:
        print(f'Failed to connect: {e}')

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
