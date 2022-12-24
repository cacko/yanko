from sys import argv

if len(argv) > 1:
    from yanko.cli import cli

    cli()
else:
    from yanko import start

    start()
