import click
import toml


@click.command()
@click.option('--config', required=False, help='Config file location')
@click.option('--verbose/-v', required=False, default=False, help='Be loud')
def main(config, verbose):
    pass
