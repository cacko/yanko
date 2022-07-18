from setuptools import setup


APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'iconfile': 'icon.icns',
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
    },
    'packages': [
        'rumps',
        'cachable',
        'dataclasses_json',
        'jsonrpcclient',
        'requests',
        'arrow',
        'tld',
    ],
}
setup(
    app=APP,
    name="Yanko",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
