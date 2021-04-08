from deezer import Deezer
from deemix.app.cli import cli
from pathlib import Path
from argparse import ArgumentParser
from logging import getLogger, WARN
from deemon.app.queuemanager import QueueManager
from deemon.app.db import DB
from deemon import __version__

import os

BITRATE = {1: 'MP3 128', 3: 'MP3 320', 9: 'FLAC'}
HOME = str(Path.home())
DB_FILE = Path(HOME + "/.config/deemon/releases.db")
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_DOWNLOAD_PATH = HOME + "/Music/deemix Music"
DEFAULT_CONFIG_PATH = HOME + "/.config/deemix"


def import_artists(file):
    if os.path.isfile(file):
        with open(file) as text_file:
            list_of_artists = text_file.read().splitlines()
            return list_of_artists
    elif os.path.isdir(file):
        list_of_artists = os.listdir(file)
        return list_of_artists
    else:
        print(f"{file}: not found")


def main():
    parser = ArgumentParser(description="Monitor artists for new releases")
    parser.add_argument('--input', dest='file', help='text file or directory of artists', required=True)
    parser.add_argument('--output', dest='download_path', help='path for downloads',
                        default=DEFAULT_DOWNLOAD_PATH)
    parser.add_argument('--config', dest='config_path', help='path to deemix config dir',
                        default=DEFAULT_CONFIG_PATH)
    parser.add_argument('--bitrate', dest='bitrate', type=int, help='1=MP3 128, 3=MP3 320, 9=FLAC', default=3)
    parser.add_argument('--version', action='version', version=f'%(prog)s-{__version__}', help='show version information')
    parser.print_usage = parser.print_help
    args = parser.parse_args()

    artists = args.file
    deemix_download_path = args.download_path
    deemix_config_path = args.config_path
    deemix_bitrate = args.bitrate

    db = DB(DB_FILE)
    database_artists = db.get_all_artists()

    dz = Deezer()
    dz_logger = getLogger('deemix')
    dz_logger.setLevel(WARN)

    active_artists = []
    queue_list = []
    new_artist = False

    for line in import_artists(artists):
        # Skip blank lines
        if line == '':
            continue

        try:
            print(f"Searching for new releases by '{line}'...", end='')
            artist = dz.api.search_artist(line, limit=1)['data'][0]
        except IndexError:
            print(f" not found")
            continue

        # Check if monitoring new artist and disable auto download
        active_artists.append(artist['id'])
        artist_exists = db.check_exists(artist_id=artist['id'])
        if not artist_exists:
            new_artist = True
            print(f" new artist detected...", end='')

        # Check for new release; add to queue if not available
        artist_new_releases = 0
        all_albums = dz.api.get_artist_albums(artist['id'])
        for album in all_albums['data']:
            album_exists = db.check_exists(album_id=album["id"])
            if not album_exists:
                if not new_artist:
                    queue_list.append(QueueManager(artist, album))
                artist_new_releases += 1
                db.add_new_release(artist['id'], album['id'])
        print(f" {artist_new_releases} releases")

    # Purge artists that are no longer being monitored
    purge_list = [x for x in database_artists if x not in active_artists]
    nb_purged = db.purge_unmonitored_artists(purge_list)
    if nb_purged:
        print(f"\nPurged {nb_purged} artist(s) from database")

    # Send queue to deemix
    if queue_list:
        print(f"\nHere we go! Starting download of {len(queue_list)} release(s):")
        app = cli(deemix_download_path, deemix_config_path)
        app.login()
        print(f"Bitrate: {BITRATE[deemix_bitrate]}\n")
        for q in queue_list:
            print(f"Downloading {q.artist_name} - {q.album_title}... ", end='')
            app.downloadLink([q.url], deemix_bitrate)
            print("done!")

    # Save changes only after download is attempted
    db.commit_and_close()


if __name__ == "__main__":
    main()
