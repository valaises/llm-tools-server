import sys
import logging

from termcolor import colored


__all__ = ['init_logger', 'info', 'error', 'warn', 'debug']


info = logging.getLogger("LLTS").info
error = logging.getLogger("LLTS").error
warn = logging.getLogger("LLTS").warning
debug = logging.getLogger("LLTS").debug


def init_logger(debug_on: bool):
    class LoggerHandler(logging.Handler):
        def emit(self, record):
            if not debug_on and record.levelno == logging.DEBUG:
                return

            level_name = record.levelname
            if record.levelno == logging.ERROR:
                level_name = colored(level_name, 'red')
            elif record.levelno == logging.WARNING:
                level_name = colored(level_name, 'yellow')

            original_levelname = record.levelname
            record.levelname = level_name
            log_entry = self.format(record)
            record.levelname = original_levelname

            sys.stderr.write(log_entry)
            sys.stderr.write("\n")
            sys.stderr.flush()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y%m%d %H:%M:%S',
        handlers=[LoggerHandler()]
    )
