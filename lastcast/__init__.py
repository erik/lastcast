import time

import pylast
import pychromecast
import click
import toml


# TODO: ...and probably other things...
APP_WHITELIST = [u'Spotify', u'Google Play Music']
SCROBBLE_THRESHOLD_PCT = 0.50
SCROBBLE_THRESHOLD_SECS = 120


class ScrobbleListener(object):
    def __init__(self, config):
        self.cast = self._get_chromecast(config.get('chromecast', {}))

        self.conn = pylast.LastFMNetwork(
            api_key=config['lastfm']['api_key'],
            api_secret=config['lastfm']['api_secret'],
            username=config['lastfm']['user_name'],
            password_hash=pylast.md5(config['lastfm']['password']))

        self.last_scrobbled = {}

    def _get_chromecast(self, config):
        # TODO: use config to grab correct chromecast
        return pychromecast.get_chromecast()

    def start(self):
        while True:
            status = self.cast.media_controller.status

            # Ignore when the player is paused or in an unknown app.
            if not status.player_is_playing or \
               self.cast.app_display_name not in APP_WHITELIST:
                continue

            self._on_status(status)

            time.sleep(5)

    def _on_status(self, status):
        meta = {
            'artist': status.artist,
            'album': status.album_name,
            'title': status.title,
        }

        # Don't scrobble the same thing over and over
        # FIXME: some bizarre people like putting songs on repeat
        if meta == self.last_scrobbled:
            print 'Already scrobbled this track.', meta
            return

        # Only scrobble if track has played 50% through (or 120 seconds,
        # whichever comes first).
        if status.current_time > SCROBBLE_THRESHOLD_SECS or \
           (status.current_time / status.duration) >= SCROBBLE_THRESHOLD_PCT:
            self._scrobble(meta)

    def _scrobble(self, track_meta):
        print 'Scrobbling track', track_meta
        self.conn.scrobble(timestamp=int(time.time()), **track_meta)
        self.last_scrobbled = track_meta


def load_config(path):
    return toml.load(path)


@click.command()
@click.option('--config', required=False, help='Config file location')
@click.option('--verbose/-v', required=False, default=False, help='Be loud')
def main(config, verbose):
    # TODO: need, you know, actual config loading.
    config = load_config('lastcast.toml')

    listener = ScrobbleListener(config)
    listener.start()


if __name__ == '__main__':
    main()
