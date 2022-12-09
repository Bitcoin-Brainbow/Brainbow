import logging
import sys
import os


FORMAT = "%(asctime)s %(levelname)s: %(message)s"  # type: str

stdout_hdlr = logging.StreamHandler(sys.stdout)  # type: logging.StreamHandler
stdout_hdlr.setFormatter(logging.Formatter(FORMAT))
stdout_hdlr.setLevel(
    logging.ERROR if os.environ.get("NW_LOG") == "ERR" else logging.INFO)

file_hdlr = logging.FileHandler(
    filename="nowallet.log", mode="w")  # type: logging.FileHandler
file_hdlr.setFormatter(logging.Formatter(FORMAT))
file_hdlr.setLevel(logging.DEBUG)

logging.basicConfig(level=logging.DEBUG, handlers=[stdout_hdlr, file_hdlr])
