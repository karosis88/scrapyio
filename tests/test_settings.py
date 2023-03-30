from pathlib import Path
from tempfile import NamedTemporaryFile

from scrapyio import default_configs
from scrapyio.settings import load_settings


def test_load_settings(monkeypatch):
    saved_defaults = open(default_configs.__file__).read()
    with NamedTemporaryFile(mode="w+", suffix=".py", dir=".") as file:
        path = Path(file.name)
        import_name = path.name[:-3]  # without .py suffix
        monkeypatch.syspath_prepend(path=path.parent)
        file.write(saved_defaults)
        file.flush()
        module = __import__(import_name)
        module.REQUEST_TIMEOUT = 10
        module.MIDDLEWARES = ["NOT A PATH"]
        load_settings(import_name)
        assert default_configs.REQUEST_TIMEOUT == 10
        assert default_configs.MIDDLEWARES == ["NOT A PATH"]
