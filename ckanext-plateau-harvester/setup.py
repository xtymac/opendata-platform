from setuptools import setup, find_packages

setup(
    name='ckanext-plateau-harvester',
    version='0.1.0',
    description='Harvest PLATEAU (3D都市モデル) metadata into CKAN datasets/resources',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='PLATEAU Team',
    author_email='plateau@example.com',
    url='https://github.com/yourorg/ckanext-plateau-harvester',
    license='AGPLv3',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.9',
    install_requires=[
        'ckanext-harvest>=1.6.0',
        'requests>=2.31.0',
    ],
    entry_points='''
        [ckan.plugins]
        plateau_harvester=ckanext.plateau_harvester.plugin:PlateauHarvesterPlugin
    ''',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
