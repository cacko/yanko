from setuptools import setup


APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'iconfile': 'icon.icns',
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
        'CFBundleIdentifier': 'net.cacko.yanko',
        'CFBundleVersion': '0.2.0'
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
        'bs4',
        'miniaudio',
        'ffmpeg-python>=0.2.0',
        'numpy>=1.23.2',
        'sounddevice>=0.4.4',
        'cffi',
        'pycparser'
    ],
}
setup(
    app=APP,
    name="Yanko",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
