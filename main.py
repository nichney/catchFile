from pathlib import Path # to resolve path
import os, threading, socket
import db #DataBase logic
import link_resolver # for magnet links
import server

def addDirectory():
    path = Path(input('Enter a directory path on your local device: ').strip()).resolve()
    
    dbm = db.DatabaseManager()
    for file in path.rglob('*'):
        if file.is_file():
            dbm.add_file(str(file))
            print(f'File {file} added to db')


def addDevice():
    key = os.urandom(32) 
    generator = link_resolver.MagnetLinkGenerator()
    magnet_link = generator.generate_magnet_link(key)

    print('Magnet-link:', magnet_link)
    print('This link contains encryption key and should be shared securely.')
    threading.Thread(target=server.start_db_server, daemon=True).start()
    print('Database sharing server started')

def download_missing_files():
    dbm = db.DatabaseManager()
    missing_files = dbm.get_missing_files()

    if not missing_files:
        print('No missing files found.')
        return

    shared_ips = dbm.get_known_ips()

    for file_hash in missing_files:
        for ip in shared_ips:
            print(f'Requesting {file_hash} from {ip}...')
            if download_file_from_peer(ip, file_hash):
                print(f'File {file_hash} downloaded!')
                break
        else:
            print(f'File {file_hash} not found on any device.')

def download_file_from_peer(host, file_hash):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host, 65432))
        client.send(file_hash.encode())  

        response = client.recv(2)
        if response == b'OK':
            file_path = f'downloads/{file_hash}' 
            os.makedirs('downloads', exist_ok=True)

            with open(file_path, 'wb') as f:
                while chunk := client.recv(4096):
                    f.write(chunk)

            client.close()
            dbm = db.DatabaseManager()
            dbm.add_file(file_path)
            return True
        else:
            print(f'File {file_hash} not found on {host}.')
            client.close()
            return False
    except Exception as e:
        print(f'Failed to download {file_hash} from {host}: {e}')
        return False


def connect2device():
    magnet_link = input("Enter link to connect device: ").strip()

    try:
        link_data, key = link_resolver.MagnetLinkGenerator.decode_link(magnet_link)
        shared_db_hash = link_data['db_hash']
        ip = link_data['ip']

        print(f'Connected to device! Shared DB hash: {shared_db_hash}')
        print(f'Encryption key (store securely!): {key.hex()}')
        
        download_shared_db(ip)

        dbm = db.DatabaseManager()
        dbm.add_device(link_data['device_id'], ip)
        download_missing_files()
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
