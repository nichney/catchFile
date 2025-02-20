# Copyright (C) 2025 Kirill Osmolovsky
from pathlib import Path # to resolve path
import os, threading, socket
import db #DataBase logic
import link_resolver # for magnet links
import server, log

logger = log.Logger().get_logger()

def addDirectory():
    path = Path(input('Enter a directory path on your local device: ').strip()).resolve()
    if not path.is_dir() or not path.exists():
        logger.error(f'{path} doesn\'t exists or not a directory')
        return
    
    dbm = db.DatabaseManager()
    for file in path.rglob('*'):
        if file.is_file():
            dbm.add_file(str(file))
            logger.info(f'File {file} added to db')
    dbm.add_directory(str(path))
    server.DownloadDaemon().notify_devices()


def addDevice():
    key = os.urandom(32) 
    generator = link_resolver.MagnetLinkGenerator()
    magnet_link = generator.generate_magnet_link(key)

    print('Magnet-link:', magnet_link)
    print('This link contains encryption key and should be shared securely.')


def connect2device():
    magnet_link = input('Enter link to connect device: ').strip()

    try:
        link_data, key = link_resolver.MagnetLinkGenerator.decode_link(magnet_link)
    except Exception as e:
        logger.error(f'Invalid magnet link: {e}')
        return

    ip = link_data['ip']
    if not ip:
        logger.error(f'Magnet link {magnet_link} missing for some information')
        return

    s = server.Server()

    logger.info(f'Connected to device! Encryption key (store securely!): {key.hex()}')
    try:
        s.download_shared_db(ip)
        for p in s.dbm.get_local_directories():
            p = Path(p)
            for file in p.rglob('*'):
                s.dbm.add_file(str(file))
        server.DownloadDaemon().notify_devices()
    except socket.timeout:
        logger.info(f"Connection to {ip} timed out!")
        return
    except Exception as e:
        logger.info(f"Failed to download shared DB: {e}")
        return

    dbm = db.DatabaseManager()
    dbm.add_device(ip)
    server.DownloadDaemon().download_missing_files()

def removeDirectory():
    '''UNSYNC FILES FROM DIRECTORY'''
    path = Path(input('Enter a directory path on your local device to remove it from sync: ').strip()).resolve()
    dbm = db.DatabaseManager()
    dbm.remove_directory(str(path))
    for file in path.rglob('*'):
        if file.is_file():
            dbm.unsync_file(str(file))
            logger.info(f'File {file} uncynsed now')

def removeFiles():
    '''DELETE FILE EVERYWHERE'''
    path = Path(input('Enter a file path on your local device to delete it on synced devices: ').strip()).resolve()
    dbm = db.DatabaseManager()
    file_hash = dbm.get_file_hash_by_path(str(path))
    dbm.remove_file(file_hash)
    dbm.remove_file_by_hash(file_hash)
    os.remove(str(path))
    server.DownloadDaemon().notify_devices()

if __name__ == '__main__':
    threading.Thread(target=server.Server().start_db_server, daemon=True).start()
    logger.info('Database sharing server started')
    threading.Thread(target=server.Server().start_file_server, daemon=True).start()
    logger.info('File sharing server started')
    threading.Thread(target=server.DownloadDaemon().monitoring, daemon=True).start()
    logger.info('Monitoring demon started')

    while True:
        print('Welcome to CatchFile 0.1a, an opensource tool for synchronizing'
           'files on all your devices. Here\'s menu:\n'
           '[ 1 ] - add directory\n[ 2 ] - add device\n[ 3 ] - connect\n[ 4 ]'
           ' - remove directory from sync\n[ 5 ] - remove files on synced devices')
        try:
            ans = int(input())
        except ValueError:
            print('Invalid input! Please, enter a number from menu.')
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
