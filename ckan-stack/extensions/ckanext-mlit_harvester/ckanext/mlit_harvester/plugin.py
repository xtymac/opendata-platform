# -*- coding: utf-8 -*-

"""Plugin entry points for MLIT-related harvesters."""

import logging

from .harvester import MLITHarvester
from .csv_file import CSVFileHarvester

log = logging.getLogger(__name__)


class MLITHarvesterPlugin(MLITHarvester):
    """Expose the MLIT harvester implementation to CKAN."""

    # All behaviour is provided by ``MLITHarvester`` (which already mixes in
    # ``HarvesterBase`` and implements the harvest interface). Keeping this
    # subclass lets the existing entry-point name continue to work.
    pass


class CSVFileHarvesterPlugin(CSVFileHarvester):
    """Expose the CSV file harvester implementation to CKAN."""

    pass
