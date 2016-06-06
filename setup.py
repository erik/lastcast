from setuptools import setup


setup(
    name='lastcast',
    version='0.0.0',
    description='TODO: Write me',
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
        'PyChromecast==0.7.3',
        'click==6.2',
        'toml==0.9.1',
    ]
)
