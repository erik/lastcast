# lastcast
Scrobble music playing on Chromecast devices to last.fm

Because I was annoyed that Spotify doesn't scrobble to last.fm when
using Chromecast. Currently will scrobble tracks playing on Spotify and Google
Play Music.

`pip install lastcast`

To setup a configuration for lastcast, either modify `example.lastcast.toml` as
necessary and write it to `~/.lastcast.toml`, or use the config creation tool:

`lastcast --wizard`

Once the configuration file is in place, run `lastcast` to connect to the
Chromecast and start scrobbling.
