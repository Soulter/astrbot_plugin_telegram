import logging, os, colorlog

log_colors_config = {
    'DEBUG': 'white',  # cyan white
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'cyan',
}

logging_level = logging.INFO
if 'DEBUG' in os.environ and os.environ['DEBUG'] == 'true':
    logging_level = logging.DEBUG

terminal_out = logging.StreamHandler()

terminal_out.setFormatter(colorlog.ColoredFormatter(
    "%(log_color)s[%(asctime)s] [%(tag)s/%(levelname)s] %(message)s",
    datefmt="%m-%d %H:%M:%S",
    log_colors=log_colors_config,
))

for t in logging.getLogger().handlers:
    logging.getLogger().removeHandler(t)

logging.getLogger().addHandler(terminal_out)
logging.getLogger().setLevel(logging_level)

logging.info("ok", extra={"tag": "telegram"})