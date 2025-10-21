import json
import logging
import time
from typing import Dict, Any
from colorama import init, Fore, Style
from typing_extensions import Annotated, Doc
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from  views.render import JsonResponseEncoder

import settings

init()

class JSONFormatter(logging.Formatter):
    def __init__(
            self,
            ecosystem: Annotated[bool, Doc("Whether to print runtime environment")] = False,
            index: Annotated[bool, Doc("Whether to print runtime location")] = False,
            datefmt: str | None = None
    ) -> None:
        self.ecosystem = ecosystem
        self.index = index
        self.datefmt = datefmt
        # Simplified format string
        fmt = '[%(name)s][%(levelname)s][%(asctime)s]%(message)s'
        super().__init__(fmt=fmt, datefmt=datefmt)

    def _build_prefix(self, record) -> str:
        """Build environment information prefix"""
        parts = []
        if self.ecosystem:
            ecosystem_parts = [
                f"{record.processName}:{record.process}" if record.process else "",
                f"{record.threadName}:{record.thread}" if record.threadName else "",
                record.taskName or ""
            ]
            parts.append(f"[{'-'.join(filter(None, ecosystem_parts))}]")

        if self.index:
            parts.append(f"[{record.pathname}:{record.lineno}<{record.funcName}>]")

        return ''.join(parts)

    def format(self, record: logging.LogRecord) -> str:

        # Basic formatting
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        levelname = record.levelname
        logger_name = record.name
        custom_datetime = str(datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])

        # Exception handling
        exc_text = ""
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)

        # JSON log
        log_data: Dict[str, Any] = {
            "timestamp": int(time.time() * 1000),
            "datetime": custom_datetime,
            "name": logger_name,
            "level": levelname,
            "pathname": record.pathname,
            "lineno": record.lineno,
            "message": record.message,
            "args": record.args,
            "exc": exc_text
        }
        return json.dumps(log_data, ensure_ascii=False, cls=JsonResponseEncoder)


class Formatter(logging.Formatter):
    __COLORS__ = {
        logging.CRITICAL: Fore.RED,
        logging.ERROR: Fore.LIGHTRED_EX,
        logging.WARNING: Fore.YELLOW,
        logging.INFO: Fore.LIGHTGREEN_EX,
        logging.DEBUG: Fore.LIGHTBLUE_EX,
        logging.NOTSET: Fore.WHITE,
    }

    def __init__(
            self,
            ecosystem: Annotated[bool, Doc("Whether to print runtime environment")] = False,
            index: Annotated[bool, Doc("Whether to print runtime location")] = False,
            datefmt: str | None = None
    ) -> None:
        self.datefmt = datefmt
        self._fmt = '[%(name)s][%(levelname)s][%(asctime)s]%(message)s'
        self._style = logging.PercentStyle(self._fmt)
        self._index = index
        self._ecosystem = ecosystem

    @staticmethod
    def ensure_once_linebreak(message: str) -> str:
        if message[-1] != '\n':
            return f'{message}\n'
        return message

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        for levelno, _color in self.__COLORS__.items():
            if record.levelno >= levelno:
                color = _color
                break
        else:
            color = Fore.WHITE
        message = f'{color}{record.message}{Style.RESET_ALL}'
        levelname = f'{color}{record.levelname}{Style.RESET_ALL}'
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message = f'{self.ensure_once_linebreak(message)}{Fore.RED}{record.exc_text}{Style.RESET_ALL}'
        if record.stack_info:
            message = f'{self.ensure_once_linebreak(message)}{Fore.RED}{record.stack_info}{Style.RESET_ALL}'
        prefix = ''
        if self._ecosystem:
            ecosystemes = [
                f'{record.processName}:{record.process}' if record.processName and record.process else '',
                f'{record.threadName}:{record.thread}' if record.threadName and record.threadName else '',
                record.taskName,
            ]
            prefix = f"[{'-'.join(filter(None, ecosystemes))}]"
        if self._index:
            prefix = f'{prefix}[{record.pathname}:{record.lineno}<{record.funcName}>]'
        return f'[{Fore.LIGHTWHITE_EX}{record.name}{Style.RESET_ALL}][{levelname}][{record.asctime}]{prefix}{message}'


def create_logger(
        name: str,
        level: int = logging.INFO,
        index: bool = False,
        ecosystem: bool = False
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.propagate = False  # Prevent duplicate logging
    if logger.handlers:
        return logger
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.LOGGING_FORMAT == "json":
        console_handler.formatter = JSONFormatter(index=index, ecosystem=ecosystem)
    else:
        console_handler.formatter = Formatter(index=index, ecosystem=ecosystem)
    logger.addHandler(console_handler)
    logger.setLevel(level)
    return logger