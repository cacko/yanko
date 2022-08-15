from setuptools import setup


APP = ['app.py']
DATA_FILES = ["./bin/ffplay"]
OPTIONS = {
    'iconfile': 'icon.icns',
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
        'CFBundleIdentifier': 'net.cacko.yanko',
        'CFBundleVersion': '0.1.0'
    },
    'packages': [
        'rumps',
        'dataclasses_json',
        'requests',
        'tld',
        'PIL',
        'appdir',
        'pyotp',
        'click',
        'pixelme',
        'cv2',
        'numpy',
        'bs4'
    ],
}
setup(
    app=APP,
    name="Yanko",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
