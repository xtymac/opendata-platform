from setuptools import find_packages, setup

setup(
    name="ckanext-cesium-viewer",
    version="0.1.0",
    description="CKAN resource view to display 3D Tiles and prebuilt Cesium web maps",
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python",
    ],
    author="",
    license="AGPL-3.0",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "requests>=2.28",
    ],
    entry_points="""
        [ckan.plugins]
        cesium_viewer=ckanext.cesium_viewer.plugin:CesiumViewerPlugin
    """,
)
