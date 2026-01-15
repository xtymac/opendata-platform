# -*- coding: utf-8 -*-

"""FIWARE Orion harvester plugin for CKAN."""

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.harvest.interfaces import IHarvester
from ckanext.fiware_orion.harvester import FiwareOrionHarvester as Harvester


class FiwareOrionHarvester(plugins.SingletonPlugin):
    """FIWARE Orion Context Broker harvester plugin."""

    plugins.implements(plugins.IConfigurer)
    plugins.implements(IHarvester)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'fiware_orion')

    # IHarvester
    def info(self):
        return Harvester().info()

    def validate_config(self, config):
        return Harvester().validate_config(config)

    def get_original_url(self, harvest_object_id):
        return Harvester().get_original_url(harvest_object_id)

    def gather_stage(self, harvest_job):
        return Harvester().gather_stage(harvest_job)

    def fetch_stage(self, harvest_object):
        return Harvester().fetch_stage(harvest_object)

    def import_stage(self, harvest_object):
        return Harvester().import_stage(harvest_object)
