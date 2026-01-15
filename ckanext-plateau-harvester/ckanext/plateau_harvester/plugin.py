"""
CKAN plugin entry point for PLATEAU Harvester
"""
import ckan.plugins as plugins
from .harvester import PlateauHarvester


class PlateauHarvesterPlugin(plugins.SingletonPlugin):
    """
    PLATEAU Harvester plugin for CKAN
    """
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.interfaces.IHarvester)

    # IHarvester
    def info(self):
        """Return harvester info (deprecated in favor of get_harvesters)"""
        return PlateauHarvester().info()

    def gather_stage(self, harvest_job):
        return PlateauHarvester().gather_stage(harvest_job)

    def fetch_stage(self, harvest_object):
        return PlateauHarvester().fetch_stage(harvest_object)

    def import_stage(self, harvest_object):
        return PlateauHarvester().import_stage(harvest_object)

    # IConfigurer
    def update_config(self, config):
        """Update CKAN configuration"""
        # Add templates directory if needed
        # plugins.toolkit.add_template_directory(config, 'templates')
        pass
