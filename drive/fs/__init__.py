# encoding: utf-8
import logging


class Partition:
    def __init__(self, type_, stream, preceding_bytes, boot_sector_parser):
        self.type = type_

        self.preceding_bytes = preceding_bytes

        self.stream = stream

        self.logger = None
        self.setup_logger()

        self.logger.info('reading boot sector')
        self.boot_sector = boot_sector_parser(stream)

    def setup_logger(self):
        self.logger = logging.getLogger(self.type)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s: %(message)s'
        ))
        self.logger.addHandler(handler)
