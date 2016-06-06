import time

import pylast
import pychromecast
import click
import toml


# TODO: ...and probably other things...
APP_WHITELIST = [u'Spotify']


class ScrobbleListener(object):
    def __init__(self, config):
        self.cast = None

        self.conn = pylast.LastFMNetwork(
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            username=config['user_name'],
            password_hash=pylast.md5(config['password']))

        self.last_status = {}

    def new_media_status(self, status):
        '''Invoked every time we get a new media event from chromecast'''

        print status.player_is_playing
        print self.cast.app_display_name

        # filter out PAUSE / whatever else
        if not status.player_is_playing or \
           self.cast.app_display_name not in APP_WHITELIST:

            print "Do not care."
            return

        meta = {
            'artist': status.artist,
            'album': status.album_name,
            'title': status.title,
        }

        # Don't scrobble the same thing over and over
        # FIXME: some bizarre people like putting songs on repeat
        if meta == self.last_status:
            print 'Already seen it.', meta
            return

        self.last_status = meta

        print 'scrobbling', meta
        self.conn.scrobble(timestamp=int(time.time()), **meta)


def load_config(path):
    return toml.load(path)


def get_chromecast(conf):
    # TODO: use config to grab correct chromecast
    return pychromecast.get_chromecast()


@click.command()
@click.option('--config', required=False, help='Config file location')
@click.option('--verbose/-v', required=False, default=False, help='Be loud')
def main(config, verbose):
    # TODO: need, you know, actual config loading.
    config = load_config('lastcast.toml')
    listener = ScrobbleListener(config['lastfm'])

    while True:
        cast = get_chromecast(config)
        listener.cast = cast
        cast.media_controller.register_status_listener(listener)

        print 'Connected to cast:', cast

        # FIXME: Can't ^C this
        cast.join()

        # Retry and whatnot
        time.sleep(5)


if __name__ == '__main__':
    main()
