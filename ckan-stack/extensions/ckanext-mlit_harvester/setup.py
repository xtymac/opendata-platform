# -*- coding: utf-8 -*-

"""Setup script for ckanext-mlit_harvester."""

import pathlib

from setuptools import find_packages, setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text(encoding="utf-8") if (HERE / "README.md").exists() else ""

setup(
    name="ckanext-mlit_harvester",
    version="0.1.0",
    description="CKAN harvester plugin for the Japan MLIT Data platform",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/example/ckanext-mlit_harvester",
    author="",
    license="AGPL-3.0-or-later",
    packages=find_packages(include=["ckanext", "ckanext.*"]),
    namespace_packages=["ckanext"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "ckanext-harvest>=1.5.0",
        "requests",
    ],
    entry_points={
        "ckan.plugins": [
            "mlit_harvester=ckanext.mlit_harvester.plugin:MLITHarvesterPlugin",
            "csv_file_harvester=ckanext.mlit_harvester.plugin:CSVFileHarvesterPlugin",
        ],
    },
)
