from setuptools import setup, find_packages

version = '0.1.0'

setup(
    name='ckanext-simplemap',
    version=version,
    description='Lightweight Leaflet-based map view for CKAN DataStore resources',
    author='Codex Assistant',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points='''
        [ckan.plugins]
        simple_map=ckanext.simplemap.plugin:SimpleMapView
    ''',
)
