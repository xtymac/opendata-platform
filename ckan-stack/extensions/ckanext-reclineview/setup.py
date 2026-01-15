from setuptools import setup, find_packages

setup(
    name="ckanext-reclineview-local",
    version="0.0.1",
    description="Local copy of CKAN recline view extension",
    packages=find_packages(),
    include_package_data=True,
    namespace_packages=['ckanext'],
    entry_points='''
        [ckan.plugins]
        recline_view=ckanext.reclineview.plugin:ReclineView
        recline_grid_view=ckanext.reclineview.plugin:ReclineGridView
        recline_graph_view=ckanext.reclineview.plugin:ReclineGraphView
        recline_map_view=ckanext.reclineview.plugin:ReclineMapView
    ''',
)
