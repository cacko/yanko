from setuptools import setup, find_packages



# setup(
#     name=__name__,
#     version=__version__,
#     author='cacko',
#     author_email='cacko@cacko.net',
#     distclass=Distribution,
#     url='http://pypi.cacko.net/simple/tick/',
#     description='whatever',
#     install_requires=[
#         "click >= 8.0.4",
#         "toml >= 0.10.2",
#         "dataclasses-json >= 0.5.6",
#         "stringcase >= 1.2.0",
#         "requests >= 2.27.1",
#         "questionary >= 1.10.0",
#         "pyfiglet >= 0.0.post1",
#         "appdir >= 0.2",
#         "PyYAML >= ^6.0",

#     ],
#     setup_requires=['wheel'],
#     python_requires=">=3.10",
#     packages=find_packages(include=['tick', 'tick.*']),
#     entry_points="""
#         [console_scripts]
#         tick=tick.cli:cli
#     """,
# )


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
}
setup(
    app=APP,
    name="Yanko",
    data_files=DATA_FILES,
    install_requires=[
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
        'ffmpeg-python >= 0.2.0',
        'numpy >= 1.23.2',
        'sounddevice >= 0.4.4',
        'cffi',
        'pycparser'
    ],
    packages=find_packages(include=['yanko', 'yanko.*', 'sounddevice.*']),
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
