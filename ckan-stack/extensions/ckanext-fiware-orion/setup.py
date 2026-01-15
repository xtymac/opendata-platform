# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

version = '0.1.0'

setup(
    name='ckanext-fiware-orion',
    version=version,
    description="FIWARE Orion Context Broker harvester for CKAN",
    long_description="""
    This extension enables CKAN to harvest context data from FIWARE Orion Context Broker
    using the NGSI v2 and NGSI-LD APIs.
    """,
    classifiers=[],
    keywords='CKAN FIWARE Orion NGSI harvester context broker',
    author='UIxAI',
    author_email='',
    url='',
    license='AGPL',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests>=2.25.0',
    ],
    entry_points='''
        [ckan.plugins]
        fiware_orion_harvester=ckanext.fiware_orion.plugin:FiwareOrionHarvester

        [babel.extractors]
        ckan = ckan.lib.extract:extract_ckan
    ''',
)
