from __future__ import print_function

import logging
import os.path
import sys
import time
import traceback

import pylast
import pychromecast
import click
import toml

from pychromecast.error import PyChromecastError


logging.basicConfig()


# TODO: ...and probably other things...
APP_WHITELIST = [u'Spotify', u'Google Play Music', u'Plex']
SCROBBLE_THRESHOLD_PCT = 0.50
SCROBBLE_THRESHOLD_SECS = 120
UNSUPPORTED_MODES = [u'MultizoneLeader']


class ScrobbleListener(object):
    def __init__(self, config):
        self.cast_config = config.get('chromecast', {})
        self._connect_chromecast(self.cast_config)

        if not self.cast:
            click.echo('Failed to connect! Exiting')
            sys.exit(1)

        self.lastfm = pylast.LastFMNetwork(
            api_key=config['lastfm']['api_key'],
            api_secret=config['lastfm']['api_secret'],
            username=config['lastfm']['user_name'],
            password_hash=pylast.md5(config['lastfm']['password']))

        self.last_scrobbled = {}
        self.last_played = {}

    def listen(self):
        while True:
            try:
                if not self.cast:
                    self._connect_chromecast(self.cast_config)
                else:
                    self.poll()
                    time.sleep(5)

            # This could happen due to network hiccups, Chromecast
            # restarting, race conditions, etc...
            #
            # Just take a nap and retry.
            except (PyChromecastError, pylast.NetworkError):
                traceback.print_exc()
                time.sleep(30)

                print('Reconnecting to cast device...')
                self.cast = None

    def poll(self):
        self.cast.media_controller.block_until_active()

        # Only certain applications make sense to scrobble.
        if self.cast.app_display_name not in APP_WHITELIST:
            return

        # Certain operating modes do not support the
        # media_controller.update_status() call. Placing a device into a cast
        # group is one such case. When running in this config, the
        # cast.app_id is reported as 'MultizoneLeader'. Ensure we skip.
        if self.cast.app_id in UNSUPPORTED_MODES:
            return

        self.cast.media_controller.update_status()
        status = self.cast.media_controller.status

        # Ignore when the player is paused.
        if not status.player_is_playing:
            return

        # Triggered when we poll in between songs (see issue #6)
        if not status.current_time or not status.duration:
            return

        self._on_status(status)

    def _connect_chromecast(self, config):
        self.cast = None
        available = pychromecast.get_chromecasts()

        if 'name' in config:
            available = [c for c in available if c.device.friendly_name == config['name']]

        if not available:
            click.echo('Could not connect to device %s\n'
                       'Available devices: %s ' % (
                           config.get('name', ''), ', '.join(available)))
            return

        if len(available) > 1:
            click.echo('WARNING: Multiple chromecasts available. Choosing first.')

        self.cast = available[0]

        # Wait for the device to be available
        self.cast.wait()
        print('Using chromecast: ', self.cast.device)

    def _on_status(self, status):
        meta = {
            'artist': status.artist,
            'album': status.album_name,
            'title': status.title,
        }

        self._now_playing(meta)

        # Only scrobble if track has played 50% through (or 120 seconds,
        # whichever comes first).
        if status.current_time > SCROBBLE_THRESHOLD_SECS or \
           (status.current_time / status.duration) >= SCROBBLE_THRESHOLD_PCT:
            self._scrobble(meta)

    def _now_playing(self, track_meta):
        if track_meta == self.last_played:
            return

        self.lastfm.update_now_playing(**track_meta)
        self.last_played = track_meta

    def _scrobble(self, track_meta):
        # Don't scrobble the same thing over and over
        # FIXME: some bizarre people like putting songs on repeat
        if track_meta == self.last_scrobbled:
            return

        print(u'Scrobbling: {artist} - {title} [{album}]'.format(**track_meta))
        self.lastfm.scrobble(timestamp=int(time.time()), **track_meta)
        self.last_scrobbled = track_meta


def load_config(path):
    config = toml.load(path)

    assert 'lastfm' in config, 'Missing lastfm config block'

    for k in ['api_key', 'api_secret', 'user_name', 'password']:
        assert k in config['lastfm'], 'Missing required lastfm option: %s' % k

    return config


def config_wizard():
    click.echo('''
You'll need to create a last.fm API application first. Do so here:

    http://www.last.fm/api/account/create

What you fill in doesn't matter at all, just make sure to save the API
Key and Shared Secret.
''')

    config = {
        'lastfm': {
            key: click.prompt(key, type=str)
            for key in ['user_name', 'password', 'api_key', 'api_secret']
        }
    }

    available = [
        cc.device.friendly_name for cc in
        pychromecast.get_chromecasts()
    ]

    if len(available) != 1 or click.confirm('Manually specify cast device?'):
        click.echo('\n\nAvailable cast devices: %s' % ', '.join(available))

        config['chromecast'] = {
            'name': click.prompt('Which device should be used?')
        }

    generated = toml.dumps(config)
    click.echo('Generated config:\n\n%s' % generated)

    if click.confirm('Write to ~/.lastcast.toml?'):
        with open(os.path.expanduser('~/.lastcast.toml'), 'w') as fp:
            fp.write(generated)


@click.command()
@click.option('--config', required=False, help='Config file location')
@click.option('--wizard', is_flag=True, help='Generate a lastcast config.')
def main(config, wizard):
    if wizard:
        return config_wizard()

    paths = [config] if config else ['./lastcast.toml', '~/.lastcast.toml']

    for path in paths:
        path = os.path.expanduser(path)
        if os.path.exists(path):
            config = load_config(path)
            break
    else:
        click.echo('Config file not found!\n\nUse --wizard to create a config')
        sys.exit(1)

    ScrobbleListener(config).listen()


if __name__ == '__main__':
    main()
