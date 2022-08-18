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
        '_sounddevice_data',
        'PIL',
        'cv2',
        'numpy'
    ],
}
setup(
    app=APP,
    name="Yanko",
    install_requires=[
        'rumps >= 0.5.9',
        'dataclasses_json >= 0.5.7',
        'requests >= 2.28.1',
        'tld >= 0.12.6',
        'pillow >= 9.2.0',
        'appdir >= 0.2',
        'pyotp >= 2.6.0',
        'click >= 8.1.3',
        'pixelme>= 0.4.7',
        'opencv-python >= 4.6.0.66',
        'bs4 >= 0.0.1',
        'miniaudio',
        'ffmpeg-python>=0.2.0',
        'numpy>=1.23.2',
        'sounddevice>=0.4.4',
        'cffi >= 1.15.1',
        'pycparser >= 2.21'
    ],
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)