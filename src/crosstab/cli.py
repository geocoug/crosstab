"""Command-line interface for crosstab.

Built on `rich-click <https://github.com/ewels/rich-click>`_ — the same Click
API with rich-formatted ``--help`` output. Uses a small ``OptionEatAll``
subclass so the multi-value flags ``-r``, ``-c``, ``-v`` behave like
``argparse``'s ``nargs="+"``: all tokens until the next flag are consumed
into a single tuple (e.g. ``-r foo bar baz``), instead of forcing the user
to repeat the flag.
"""

from __future__ import annotations

import logging
from pathlib import Path

import rich_click as click
from rich.logging import RichHandler

from crosstab import __version__
from crosstab.crosstab import Crosstab

logger = logging.getLogger("crosstab")


class OptionEatAll(click.Option):
    """A Click ``Option`` that consumes every token up to the next flag.

    This restores the ``argparse(nargs="+")`` style where one flag can be
    followed by several whitespace-separated values: ``-r col_a col_b col_c``
    rather than ``-r col_a -r col_b -r col_c``. The captured values are
    returned as a tuple of strings.

    Adapted from the well-known Stack Overflow recipe
    (https://stackoverflow.com/a/48394004) and updated for Click 8.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._previous_parser_process = None
        self._eat_all_parser = None

    def add_to_parser(self, parser: click.parser._OptionParser, ctx: click.Context) -> None:  # type: ignore[override]
        def parser_process(value: str, state: click.parser.ParsingState) -> None:
            collected = [value]
            while state.rargs:
                token = state.rargs[0]
                if any(token.startswith(prefix) for prefix in self._eat_all_parser.prefixes):
                    break
                collected.append(state.rargs.pop(0))
            self._previous_parser_process(tuple(collected), state)

        super().add_to_parser(parser, ctx)
        # Click registers a parser entry under every name in self.opts; pick
        # the first one and re-route its process callback. Required Click
        # options always have at least one entry, so the next() default is
        # defensive only.
        opt_parser = next(
            (
                parser._long_opt.get(name) or parser._short_opt.get(name)
                for name in self.opts
                if parser._long_opt.get(name) is not None or parser._short_opt.get(name) is not None
            ),
            None,
        )
        if opt_parser is None:  # pragma: no cover
            return
        self._eat_all_parser = opt_parser
        self._previous_parser_process = opt_parser.process
        opt_parser.process = parser_process

    def type_cast_value(self, ctx: click.Context, value: object) -> object:
        """Cast each captured token through ``self.type`` rather than the
        whole tuple. Click's default behavior would call ``str(tuple_value)``
        and treat that repr as a single value, mangling the input.
        """
        if value is None:  # pragma: no cover
            # Required options always have a value once the CLI parses
            # successfully; this fallback is defensive.
            return () if self.required else None
        if not isinstance(value, tuple):  # pragma: no cover
            # ``parser_process`` always hands us a tuple; coerce defensively.
            value = (value,)
        return tuple(self.type(item, self, ctx) for item in value)


def _configure_logging(*, quiet: bool, debug: bool, logfile: Path | None) -> None:
    """Wire the package logger to the requested sinks and level.

    Handlers are reset on each call so repeated invocations in the same
    process (most notably under tests using ``CliRunner``) don't pile up
    duplicate output.
    """
    logger.handlers.clear()
    logger.propagate = False

    if not quiet:
        # Only show the level prefix (INFO/DEBUG/...) in debug mode; the
        # default run hides it so plain INFO messages render as bare text.
        logger.addHandler(
            RichHandler(
                show_time=False,
                show_path=False,
                show_level=debug,
                markup=False,
            ),
        )
    if logfile is not None:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(name)s (%(lineno)d) %(levelname)s: %(message)s",
                datefmt="[%Y-%m-%d %H:%M:%S]",
            ),
        )
        logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG if debug else logging.INFO)


@click.command(
    name="crosstab",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "-f",
    "--input",
    "incsv",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
    required=True,
    help="Input CSV file.",
)
@click.option(
    "-r",
    "--row",
    "row_headers",
    cls=OptionEatAll,
    metavar="COL [COL ...]",
    required=True,
    help="One or more column names to use as row headers.",
)
@click.option(
    "-c",
    "--col",
    "col_headers",
    cls=OptionEatAll,
    metavar="COL [COL ...]",
    required=True,
    help="One or more column names to use as column headers.",
)
@click.option(
    "-v",
    "--value",
    "value_cols",
    cls=OptionEatAll,
    metavar="COL [COL ...]",
    required=True,
    help="One or more column names whose values fill the crosstab cells.",
)
@click.option(
    "-o",
    "--output",
    "outxlsx",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    default=None,
    help="Output XLSX file. Defaults to <input>_crosstab.xlsx.",
)
@click.option(
    "--fill",
    "fill",
    type=str,
    default=None,
    help="Value to write into empty cells. Empty by default.",
)
@click.option(
    "-s",
    "--keep-src",
    is_flag=True,
    default=False,
    help="Include a sheet with the verbatim source data.",
)
@click.option(
    "-k",
    "--keep-duckdb",
    is_flag=True,
    default=False,
    help="Persist the DuckDB database to <input>.duckdb so it can be queried later.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    default=False,
    help="Suppress all console output.",
)
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.option(
    "-l",
    "--log",
    "logfile",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, path_type=Path),
    default=None,
    help="Log all output to a file.",
)
@click.version_option(__version__, "--version", prog_name="crosstab", message="%(prog)s %(version)s")
def app(
    incsv: Path,
    row_headers: tuple[str, ...],
    col_headers: tuple[str, ...],
    value_cols: tuple[str, ...],
    outxlsx: Path | None,
    fill: str | None,
    keep_src: bool,
    keep_duckdb: bool,
    quiet: bool,
    debug: bool,
    logfile: Path | None,
) -> None:
    """Rearrange data from a normalized CSV to a crosstabulated XLSX workbook."""
    _configure_logging(quiet=quiet, debug=debug, logfile=logfile)
    try:
        Crosstab(
            incsv=incsv,
            outxlsx=outxlsx,
            row_headers=row_headers,
            col_headers=col_headers,
            value_cols=value_cols,
            fill=fill,
            keep_src=keep_src,
            keep_duckdb=keep_duckdb,
        ).crosstab()
    except ValueError as exc:
        logger.error(f"ValueError: {exc}")
        raise click.exceptions.Exit(code=1) from exc
    except Exception as exc:
        logger.exception(f"Uncaught exception: {exc}")
        raise click.exceptions.Exit(code=1) from exc


if __name__ == "__main__":  # pragma: no cover
    app()
