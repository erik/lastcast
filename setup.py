from setuptools import setup


setup(
    name='lastcast',
    version='0.5.0',
    description='Scrobble music to last.fm from Chromecast.',
    author='Erik Price',
    url='https://github.com/erik/lastcast',
    packages=['lastcast'],
    entry_points={
        'console_scripts': [
            'lastcast = lastcast:main',
        ],
    },
    license='MIT',
    install_requires=[
        'PyChromecast==0.8.0',
        'click==6.2',
        'pylast==1.7.0',
        'toml==0.9.1',
    ]
)
