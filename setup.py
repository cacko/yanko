from setuptools import setup


APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'iconfile': 'icon.icns',
    'argv_emulation': True,
    'plist': {
        'LSBackgroundOnly': True,
    },
    'packages': [
        'rumps',
        'dataclasses_json',
        'requests',
        'tld',
        'cachable',
        'PIL',
        'appdir',
        'pyotp',
        'cv2',
        'numpy',
        'pynput'
    ],
}
setup(
    app=APP,
    name="Yanko",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
