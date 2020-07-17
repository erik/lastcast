lastcast
========

Scrobble music playing on Chromecast devices to last.fm and libre.fm.

By default, lastcast will scrobble music playing on Spotify,
Google Play Music, SoundCloud, Plex, and YouTube Music but can
be configured to scrobble any media player that supports Chromecast.

**A Note for Spotify Users:**

Last.fm now has `first class
support <https://support.last.fm/t/spotify-scrobbling/189>`_
for Spotify, and you should probably use this rather than lastcast.

**Python 3.5 and earlier are no longer supported as of lastcast 1.0.0.**

If you need Python 2, please install ``lastcast==0.7.0``.

Getting started
---------------

``pip3 install lastcast``

Set up an initial configuration with the configuration
creation tool:

``lastcast --wizard``

If you'd prefer to set up the configuration manually, modify
``example.lastcast.toml`` from the repo and save it to
``~/.lastcast.toml``.

Once the configuration file is in place, just run ``lastcast`` to connect to
the Chromecast and start scrobbling!

Linux / systemd instructions
----------------------------

1. ``sudo pip3 install --upgrade lastcast``
2. ``lastcast --wizard``
3. Edit the code block below as needed (remember to fill in the config path!)
   and write to ``/usr/lib/systemd/system/lastcast.service``
   (or ``/etc/systemd/system/lastcast.service`` if the directory doesn't exist)
4. ``sudo systemctl daemon-reload``
5. ``sudo systemctl enable lastcast``

.. code-block:: ini

   [Unit]
   Description=lastcast
   Requires=networking.service
   After=network-online.target
   Wants=network-online.target

   [Service]
   ExecStart=/usr/local/bin/lastcast --config [PATH TO lastcast.toml]
   Restart=always
   RestartSec=5
   # Set this to run as your user rather than root!
   User=pi

   [Install]
   WantedBy=multi-user.target

Linux / systemd troubleshooting
-------------------------------

If your lastcast installation is not scrobbling check its log calling ``journalctl -f _COMM=lastcast``

If you see the following error

.. code-block:: bash

    RuntimeError: Click will abort further execution because Python 3 was
    configured to use ASCII as encoding for the environment.

    This system supports the C.UTF-8 locale which is recommended.
    You might be able to resolve your issue by exporting the
    following environment variables:

    export LC_ALL=C.UTF-8
    export LANG=C.UTF-8

modify the ``lastcast.service`` file you created in the previous section as by adding the following
to the ``[Service]`` section

.. code-block:: ini

    Environment="LC_ALL=C.UTF-8"
    Environment="LANG=C.UTF-8"

Detailed macOS setup
--------------------

(for anyone not familiar with Python and pip)

Enter the following commands in your Terminal (Terminal.app, iTerm2, etc.):

1. ``brew install python3``
2. ``sudo pip3 install --upgrade lastcast``
3. ``lastcast --wizard``

This will prompt you to create a last.fm API application and then ask for your
login information, which will only be stored locally on your computer.

You may get an error on step 2 about ``cc`` missing. If this is the case,
install xcode by running ``xcode-select --install`` and retry step 2.

Now everything should be set up. When you want to start scrobbling, simply
run ``lastcast`` in the terminal.

Docker setup
------------

``lastcast`` uses a Docker volume in order to link the configuration file
into the container.

.. code:: bash

   # Path to configuration file. Make sure to use an absolute path.
   export CONFIG_PATH=/path/to/your/lastcast.toml

   docker pull rkprc/lastcast

   docker run -it                   \
     --net=host                     \
     --name lastcast                \
     -v $CONFIG_PATH:/lastcast.toml \
     rkprc/lastcast

   # If you need to generate a config file, run the wizard:
   docker run -it                   \
     --net=host                     \
     -v $CONFIG_PATH:/lastcast.toml \
     rkprc/lastcast                 \
     lastcast --wizard

No Chromecast devices found?
----------------------------

It is possible that an incompatible version of ``netifaces`` will prevent lastcast
from finding any Chromecast devices on your network. This is known to affect
Windows 10 with ``netifaces==0.10.5`` installed.

The fix, as described in `this StackOverflow answer
<http://stackoverflow.com/a/41517483>`_ is simply to uninstall the wrong version
and manually install ``netifaces==0.10.4``.

.. code:: bash

   $ pip uninstall netifaces
   $ pip install netifaces==0.10.4

If you still can't discover any Chromecasts, please `open an issue
<https://github.com/erik/lastcast/issues/new>`_.
