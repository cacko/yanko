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
        "pyfiglet >= 0.8.post1",
        "PyGObject >= 3.42.1",
        "requests >= 2.28.1",
        "packaging >= 21.3",
        "PyYAML >= 6.0",
        "py2app >= 0.28.2",
        "toml >= 0.10.2",
        "tld >= 0.12.6",
        "arrow >= 1.2.2",
        "dataclasses-json >= 0.5.7",
        "rumps >= 0.5.9",
        "bottle >= 0.12.21",
        "Pillow >= 9.2.0",
        "appdir >= 0.2",
        "pyotp >= 2.6.0",
        "click >= 8.1.3",
        "pixelme >= 0.4.7",
        "bs4 >= 0.0.1",
        "miniaudio >= 1.52",
        "ffmpeg-python >= 0.2.0",
        "numpy >= 1.23.2",
        "sounddevice >= 0.4.4",
        "pycparser",
        "cffi"
    ],
    packages=find_packages(include=['yanko', 'yanko.*', 'sounddevice.*']),
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
