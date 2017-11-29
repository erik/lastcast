import logging
import os.path
import sys
import time
import traceback

import click
import pylast
import pychromecast
import toml

from pychromecast.error import PyChromecastError


logging.basicConfig()

# Default set of apps to scrobble from.
APP_WHITELIST = [u'Spotify', u'Google Play Music', u'SoundCloud', u'Plex']

SCROBBLE_THRESHOLD_PCT = 0.50
SCROBBLE_THRESHOLD_SECS = 120
UNSUPPORTED_MODES = {'MultizoneLeader'}
POLL_INTERVAL = 5.0


class ScrobbleListener(object):
    def __init__(self, config, cast_name, available_devices=None):
        self.cast_name = cast_name
        self.cast_config = config.get('chromecast', {})
        self.app_whitelist = self.cast_config.get('app_whitelist', APP_WHITELIST)

        self._connect_chromecast(available_devices)

        if not self.cast:
            click.echo('Failed to connect! Exiting')
            sys.exit(1)

        self.scrobblers = []

        if 'lastfm' in config:
            self.scrobblers.append(pylast.LastFMNetwork(
                api_key=config['lastfm']['api_key'],
                api_secret=config['lastfm']['api_secret'],
                username=config['lastfm']['user_name'],
                password_hash=pylast.md5(config['lastfm']['password'])))

        if 'librefm' in config:
            self.scrobblers.append(pylast.LibreFMNetwork(
                session_key=config['librefm']['session_key'],
                username=config['librefm']['user_name'],
                password_hash=pylast.md5(config['librefm']['password'])
            ))

        self.last_scrobbled = {}
        self.current_track = {}
        self.current_time = 0
        self.last_poll = time.time()

        self.estimate_spotify_timestamp = self.cast_config.get('estimate_spotify_timestamp', True)

    def poll(self):
        try:
            if not self.cast:
                self._connect_chromecast()
            else:
                self._poll()

        # This could happen due to network hiccups, Chromecast
        # restarting, race conditions, etc...
        except (PyChromecastError, pylast.NetworkError):
            traceback.print_exc()

            click.echo('Reconnecting to cast device `%s`...' % self.cast_name)
            self.cast = None

    def _poll(self):
        current_app = self.cast.app_display_name

        # Only certain applications make sense to scrobble.
        if current_app not in self.app_whitelist:
            return

        # Certain operating modes do not support the
        # `media_controller.update_status()` call. Placing a device into a cast
        # group is one such case. When running in this config, the cast.app_id
        # is reported as 'MultizoneLeader'. Ensure we skip.
        if self.cast.app_id in UNSUPPORTED_MODES:
            return

        # This can raise an exception when device is part of a multizone group
        # (apparently `app_id` isn't sufficient)
        try:
            self.cast.media_controller.update_status()
        except pychromecast.error.UnsupportedNamespace:
            return

        status = self.cast.media_controller.status

        # Ignore when the player is paused.
        if not status.player_is_playing:
            return

        # Triggered when we poll in between songs (see issue #6)
        if status.current_time is None or status.duration is None or \
           status.duration <= 0:
            return

        # Spotify doesn't reliably report timestamps (see #20, #27),
        # so we estimate the current time as best we can
        last_poll, self.last_poll = (self.last_poll, time.time())

        if self.estimate_spotify_timestamp and current_app == 'Spotify':
            self.current_time += time.time() - last_poll

        else:
            self.current_time = status.current_time

        self._on_status(status)

    def _connect_chromecast(self, available_devices=None):
        self.cast = None

        if not available_devices:
            available_devices = pychromecast.get_chromecasts()

        matching_devices = [
            c for c in available_devices
            if c.device.friendly_name == self.cast_name
        ]

        if not matching_devices:
            names = [d.device.friendly_name for d in available_devices]
            click.echo('Could not connect to device %s\n'
                       'Available devices: %s ' % (self.cast_name, ', '.join(names)))
            return

        if len(matching_devices) > 1:
            click.echo('WARNING: Multiple chromecasts available. Choosing first.')

        self.cast = matching_devices[0]

        # Wait for the device to be available
        self.cast.wait()
        click.echo('Using chromecast: %s' % self.cast.device.friendly_name)

    def _on_status(self, status):
        meta = {
            'artist': status.artist if status.artist else status.album_artist,
            'album': status.album_name,
            'title': status.title,
        }

        self._now_playing(meta)

        # Only scrobble if track has played 50% through (or 120 seconds,
        # whichever comes first).
        if self.current_time > SCROBBLE_THRESHOLD_SECS or \
           (self.current_time / status.duration) >= SCROBBLE_THRESHOLD_PCT:
            self._scrobble(meta)

    def _now_playing(self, track_meta):
        # Only need to update the now playing once for each track
        if track_meta == self.current_track:
            return

        for scrobbler in self.scrobblers:
            try:
                scrobbler.update_now_playing(**track_meta)
            except (pylast.NetworkError, pylast.MalformedResponseError):
                logging.exception('update_now_playing failed for %s', scrobbler.name)

        self.current_track = track_meta

        # First time this track has been seen, so reset the estimated
        # current time if we're using the spotify hack
        if self.cast.app_display_name == 'Spotify' and \
           self.estimate_spotify_timestamp:
            # Assume the track did not start in sync with the poll interval
            self.current_time = POLL_INTERVAL / 2

    def _scrobble(self, track_meta):
        # Don't scrobble the same thing over and over
        # FIXME: some bizarre people like putting songs on repeat
        if track_meta == self.last_scrobbled:
            return

        click.echo(u'Scrobbling: {artist} - {title} [{album}]'.format(**track_meta))

        for scrobbler in self.scrobblers:
            try:
                scrobbler.scrobble(timestamp=int(time.time()), **track_meta)
            except (pylast.NetworkError, pylast.MalformedResponseError):
                logging.exception('scrobble failed for %s', scrobbler.name)

        self.last_scrobbled = track_meta


def load_config(path):
    config = toml.load(path)

    assert 'lastfm' in config, 'Missing lastfm config block'

    for k in ['api_key', 'api_secret', 'user_name', 'password']:
        assert k in config['lastfm'], 'Missing required lastfm option: %s' % k

    return config


def config_wizard():
    config = {'chromecast': {}}

    if click.confirm('Set up last.fm account?', default=True):
        click.echo('''
You'll need to create a last.fm API application first. Do so here:

    http://www.last.fm/api/account/create

What you fill in doesn't matter at all, just make sure to save the API
Key and Shared Secret.
''')

        config['lastfm'] = {
            key: click.prompt(key, type=str, hide_input=hidden)
            for (key, hidden) in [
                    ('user_name', False),
                    ('password', True),
                    ('api_key', False),
                    ('api_secret', True)
            ]
        }

    if click.confirm('Set up Libre.fm account?'):
        libre_conf = {
            key: click.prompt(key, type=str, hide_input=hidden)
            for (key, hidden) in [
                    ('user_name', False),
                    ('password', True)
            ]
        }

        libre = pylast.LibreFMNetwork(
            username=libre_conf['user_name'],
            password_hash=pylast.md5(libre_conf['password']))

        skg = pylast.SessionKeyGenerator(libre)
        url = skg.get_web_auth_url()

        click.echo('''Please grant lastcast access to your Libre.fm account:

        %s
''' % url)

        click.echo('Hit enter when ready')
        click.getchar()

        libre_conf['session_key'] = skg.get_web_auth_session_key(url)
        config['librefm'] = libre_conf

    available = [
        cc.device.friendly_name for cc in
        pychromecast.get_chromecasts()
    ]

    if len(available) == 1:
        config['chromecast']['devices'] = [available[0]]

    if len(available) > 1 or click.confirm('Manually specify cast device?', default=True):
        click.echo('\n\nAvailable cast devices: %s' % ', '.join(available))
        device_names = click.prompt('Which device(s) should be used? (comma separated)')
        device_names = [d.strip() for d in device_names.split(',') if d.strip != '']

        config['chromecast']['devices'] = device_names

    click.echo('\n\nDefault chromecast apps to scrobble from: %s' %
               ', '.join(APP_WHITELIST))

    apps = click.prompt('Comma separated apps [blank for default]')
    apps = [app.strip() for app in apps.split(',') if app.strip() != '']

    if apps:
        config['chromecast']['app_whitelist'] = apps

    generated = toml.dumps(config)
    click.echo('Generated config:\n\n%s' % generated)

    if click.confirm('Write to ~/.lastcast.toml?', default=True):
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

    cast_config = config.get('chromecast', {})
    device_names = cast_config.get('devices', [])

    # `name` is the legacy parameter name, supporting it for now.
    if not device_names and 'name' in cast_config:
        device_names = [cast_config['name']]

    if not device_names:
        click.echo('Need to specify either `devices` or `name` in '
                   '`[chromecast]` config block!')
        sys.exit(1)

    available = pychromecast.get_chromecasts()
    listeners = [
        ScrobbleListener(config, name, available_devices=available)
        for name in device_names
    ]

    while True:
        for listener in listeners:
            listener.poll()

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
