import errno
import types
import typing as t
import sys
from pathlib import Path
import toml
import os
from appdir import get_app_dir

def import_string(import_name: str, silent: bool = False) -> t.Any:
    import_name = import_name.replace(":", ".")
    try:
        try:
            __import__(import_name)
        except ImportError:
            if "." not in import_name:
                raise
        else:
            return sys.modules[import_name]

        module_name, obj_name = import_name.rsplit(".", 1)
        module = __import__(module_name, globals(), locals(), [obj_name])
        try:
            return getattr(module, obj_name)
        except AttributeError as e:
            raise ImportError(e) from None

    except ImportError as e:
        if not silent:
            raise ValueError(import_name, e).with_traceback(
                sys.exc_info()[2]
            ) from None

    return None


class ConfigAttribute:
    """Makes an attribute forward to the config"""

    def __init__(
        self,
        name: str,
        get_converter: t.Optional[t.Callable] = None
    ):
        self.__name__ = name
        self.get_converter = get_converter

    def __get__(self, obj: t.Any, owner: t.Any = None) -> t.Any:
        if obj is None:
            return self
        rv = obj.config[self.__name__]
        if self.get_converter is not None:
            rv = self.get_converter(rv)
        return rv

    def __set__(self, obj: t.Any, value: t.Any) -> None:
        obj.config[self.__name__] = value


class Config(dict):

    def __init__(self, root, defaults: t.Optional[dict] = None):
        dict.__init__(self, defaults or {})
        self.root_path: Path = root
        if not self.root_path.exists():
            self.root_path.mkdir(parents=True)

    def from_pyfile(self, filename: str, silent: bool = False) -> bool:
        filename = (self.root_path / filename).absolute().as_posix()
        d = types.ModuleType("config")
        d.__file__ = filename
        try:
            with open(filename, mode="rb") as config_file:
                exec(compile(config_file.read(), filename, "exec"), d.__dict__)
        except OSError as e:
            if silent and e.errno in (
                    errno.ENOENT,
                    errno.EISDIR,
                    errno.ENOTDIR):
                return False
            e.strerror = f"Unable to load configuration file ({e.strerror})"
            raise
        self.from_object(d)
        return True

    def from_file(
        self,
        filename: str,
        load: t.Callable[[t.IO[t.Any]], t.Mapping],
        silent: bool = False,
    ) -> bool:
        """Update the values in the config from a file that is loaded
        using the ``load`` parameter. The loaded data is passed to the
        :meth:`from_mapping` method.
        .. code-block:: python
            import json
            app.config.from_file("config.json", load=json.load)
            import toml
            app.config.from_file("config.toml", load=toml.load)
        :param filename: The path to the data file. This can be an
            absolute path or relative to the config root path.
        :param load: A callable that takes a file handle and returns a
            mapping of loaded data from the file.
        :type load: ``Callable[[Reader], Mapping]`` where ``Reader``
            implements a ``read`` method.
        :param silent: Ignore the file if it doesn't exist.
        :return: ``True`` if the file was loaded successfully.
        .. versionadded:: 2.0
        """
        filename = os.path.join(self.root_path, filename)

        try:
            with open(filename) as f:
                obj = load(f)
        except OSError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False

            e.strerror = f"Unable to load configuration file ({e.strerror})"
            raise

        return self.from_mapping(obj)

    def from_mapping(
        self, mapping: t.Optional[t.Mapping[str, t.Any]] = None, **kwargs: t.Any
    ) -> bool:
        """Updates the config like :meth:`update` ignoring items with non-upper
        keys.
        :return: Always returns ``True``.
        .. versionadded:: 0.11
        """
        mappings: t.Dict[str, t.Any] = {}
        if mapping is not None:
            mappings.update(mapping)
        mappings.update(kwargs)
        for key, value in mappings.items():
            self[key] = value
        return True

    def from_toml(self, filename="config.toml"):
        self.from_file(filename, load=toml.load)

    def from_object(self, obj: t.Union[object, str]) -> None:
        if isinstance(obj, str):
            obj = import_string(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def get_namespace(
        self,
        namespace: str,
        lowercase:
        bool = True,
        trim_namespace: bool = True
    ) -> t.Dict[str, t.Any]:
        rv = {}
        for k, v in self.items():
            if not k.startswith(namespace):
                continue
            if trim_namespace:
                key = k[len(namespace):]
            else:
                key = k
            if lowercase:
                key = key.lower()
            rv[key] = v
        return rv

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {dict.__repr__(self)}>"


class app_config_meta(type):
    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def get(cls, var, *args, **kwargs):
        return cls().getvar(var, *args, **kwargs)

    @property
    def app_dir(cls):
        return Path(get_app_dir("Yanko")).expanduser()

class app_config(object, metaclass=app_config_meta):

    _config = None

    def __init__(self) -> None:
        self._config = Config(__class__.app_dir)
        self._config.from_toml("config.toml")

    def getvar(self, var, *args, **kwargs):
        return self._config.get(var, *args, *kwargs)
