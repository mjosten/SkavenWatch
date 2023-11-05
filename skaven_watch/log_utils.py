"""
Just a little logging utility
"""

import logging
from logging.handlers import TimedRotatingFileHandler
import os

def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    #create logs directory if doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # create a handler for logging to a file with rotation
    fh = TimedRotatingFileHandler('logs/skaven_watch.log', when='midnight', interval=1, backupCount=5)
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    
    # add handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


if __name__ == "__main__":
    logger = setup_logger("test_logger")
    logger.info("test info")
    logger.warn("test warn")
    logger.error("test error")