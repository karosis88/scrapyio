import asyncio
import logging
import typing

import click

log = logging.getLogger("scrapyio")


@click.group()
def cli():
    ...


@cli.command()
@click.argument("name")
def new(name):
    from pathlib import Path

    from scrapyio.settings import SETTINGS_FILE_NAME, SPIDERS_FILE_NAME
    from scrapyio.templates import configuration_template, spider_file_template

    path = Path.cwd()
    dir_path = path / name
    dir_path.mkdir()
    settings_file = dir_path / SETTINGS_FILE_NAME
    settings_file.touch()
    settings_file.write_text(open(configuration_template.__file__).read())
    spiders_file = dir_path / SPIDERS_FILE_NAME
    spiders_file.write_text(open(spider_file_template.__file__).read())


@cli.command()
@click.argument("spider")
@click.option("-j", "--json", type=str, help="Json file path")
@click.option("-c", "--csv", type=str, help="Csv file path")
@click.option("-s", "--sql", type=str, help="SQL URI supported by SQLAlchemy")
@click.option("-d", "--delay", type=int, help="Engine loop delay")
def run(
    spider: str,
    json: typing.Optional[str],
    csv: typing.Optional[str],
    sql: typing.Optional[str],
    delay: typing.Optional[int],
):
    from scrapyio.engines import Engine
    from scrapyio.exceptions import SpiderNotFoundException
    from scrapyio.item_loaders import (
        BaseLoader,
        CSVLoader,
        JSONLoader,
        SQLAlchemyLoader,
    )
    from scrapyio.items import ItemManager

    log.info("Running the spider")

    try:
        log.debug("Trying to import spiders file")
        import spiders  # type: ignore[import]

        log.debug("Spiders file was imported")
    except ImportError:
        log.debug("When attempting to import the spiders file, an exception was raised")
        raise SpiderNotFoundException(
            "File `spiders.py` was not found, make sure you're "
            "calling scrapyio from the directory scrapyio created."
        )

    spider_class = getattr(spiders, spider, None)

    if spider_class is None:
        raise SpiderNotFoundException(
            "Spider `%s` was not " "found in the `spiders.py` file" % spider
        )

    loaders: typing.List[BaseLoader] = []
    loader: BaseLoader
    if delay is None:
        delay = 0

    if json is not None:
        log.debug("Creating the JSON loader")
        loader = JSONLoader(filename=json)
        loaders.append(loader)

    if csv is not None:
        log.debug("Creating the CSV loader")
        loader = CSVLoader(filename=csv)
        loaders.append(loader)

    if sql is not None:
        log.debug("Creating the SQL loader")
        loader = SQLAlchemyLoader(url=sql)
        loaders.append(loader)

    item_manager = ItemManager(loaders=loaders)
    log.debug("Creating the Engine instance")
    engine = Engine(spider=spider_class(), items_manager=item_manager, loop_delay=delay)
    log.info("Running engine")
    asyncio.run(engine.run())
