import click
from requests import get
from requests.exceptions import ConnectionError
from pathlib import Path
from yanko.core.cachable import Cache, CacheType
from yanko.core.config import app_config
from yanko.db.base import YankoDb
from yanko.sonic import Command
from yanko.sonic.beats import Beats
from yanko.player.bpm import Beats as BeatsExtractor
from yanko.sonic.coverart import CoverArtFile


class YankoCommand(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)


@click.group(cls=YankoCommand)
def cli():
    """This script showcases different terminal UI helpers in Click."""
    pass


@cli.command("config", short_help="Config")
def cli_config():
    input()


@cli.command("command", short_help="Api command")
@click.argument("command")
def cli_command(command: str):
    """Shows a main menu."""
    try:
        cmd = Command(command)
        port = app_config.get("api", {}).get("port")
        resp = get(f"http://127.0.0.1:{port}/command/{cmd.value}")
        return resp.status_code
    except ValueError:
        click.echo(click.style("not valid command", fg="red"))
    except ConnectionError:
        click.echo(click.style("yanko is not running", fg="red"))


@cli.command("search", short_help="Api command")
@click.argument("query", nargs=-1)
def cli_search(query: str):
    """Shows a main menu."""
    try:
        port = app_config.get("api", {}).get("port")

        search_query = " ".join(query)
        resp = get(f"http://127.0.0.1:{port}/search/{search_query}")
        click.echo(resp.content)
    except ValueError:
        click.echo(click.style("not valid command", fg="red"))
    except ConnectionError:
        click.echo(click.style("yanko is not running", fg="red"))


@cli.command("dbinit", short_help="Init DB")
@click.option("-d", "--drop_table", default=None)
def cli_dbinit(drop_table: str):
    try:
        from yanko.db.models import Album, Artist, ArtistInfo, Beats

        with YankoDb.db as db:
            # drop_tables = [ArtistInfo]
            # # if drop_table:
            # #     drop_tables.append(drop_table)
            if drop_table:
                db.drop_tables([Beats, Artist, Album, ArtistInfo])
            db.create_tables([Beats, Artist, Album, ArtistInfo])
    except Exception as e:
        print(e)


@cli.command("reset")
def cli_reset():
    pass


@cli.command("beats", short_help="Extract Beats")
@click.argument("path")
def cli_beats(path: str):
    try:
        file_path = Path(path)
        assert file_path.exists()
        store_root = app_config.get("store", {}).get("music", "")
        BeatsExtractor.register(store_root=store_root)
        beats = Beats(
            path=f"{file_path.relative_to(store_root).as_posix()}",
            allow_extract=True
        )
        click.echo(beats.extract())
    except Exception as e:
        print(e)


@cli.command("cache", short_help="Cache")
@click.option("-d", "--delete", default=None)
def cli_cache(delete: str):
    cache_struct = Cache(
        cover_art=CacheType(name="cover_art", count=0, size=0),
        cover_icon=CacheType(name="cover_icon", count=0, size=0),
        beats_json=CacheType(name="beats_json", count=0, size=0),
    )
    for fp in app_config.cache_dir.glob("*"):
        parts = fp.name.split(".")
        cls = parts[0]
        if cls == CoverArtFile.__name__:
            if fp.stem.endswith("_icon"):
                cache_struct.cover_icon.add(fp)
            else:
                cache_struct.cover_art.add(fp)
        if fp.name.endswith("json"):
            cache_struct.beats_json.add(fp)

    if delete:
        getattr(cache_struct, delete).clear()
    else:
        print(cache_struct.to_table())
