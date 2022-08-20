from ast import arguments
import click
from yanko.core.config import app_config
from yanko.sonic import Command
from requests import get
from requests.exceptions import ConnectionError
import semver
from pathlib import Path

class YankoCommand(click.Group):

    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)


@click.group(cls=YankoCommand)
def cli():
    """This script showcases different terminal UI helpers in Click."""
    pass

@cli.command('increment_version', short_help="Increment version")
def cli_inc_version():
    init = Path(__file__).parent / "version.py"
    _, v = init.read_text().split(' = ')
    cv = semver.VersionInfo.parse(v.strip('"'))
    init.write_text(f'__version__ = "{cv.bump_patch()}"')

@cli.command('config', short_help="Config")
def cli_config():
    print('this is config')
    input()

@cli.command('command', short_help="Api command")
@click.argument('command')
def cli_command(command: str):
    """Shows a main menu."""
    try:
        cmd = Command(command)
        port = app_config.get("api", {}).get("port")
        resp = get(f"http://127.0.0.1:{port}/command/{cmd.value}")
        return resp.status_code
    except ValueError:
        click.echo(click.style("not valid command", fg='red'))
    except ConnectionError:
        click.echo(click.style("yanko is not running", fg='red'))

@cli.command('search', short_help="Api command")
@click.argument('query', nargs=-1)
def cli_search(query: str):
    """Shows a main menu."""
    try:
        port = app_config.get("api", {}).get("port")

        search_query = ' '.join(query)
        resp = get(f"http://127.0.0.1:{port}/search/{search_query}")
        click.echo(resp.content)
    except ValueError:
        click.echo(click.style("not valid command", fg='red'))
    except ConnectionError:
        click.echo(click.style("yanko is not running", fg='red'))


