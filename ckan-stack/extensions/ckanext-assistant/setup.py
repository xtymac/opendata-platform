from setuptools import find_packages, setup

setup(
    name="ckanext-assistant",
    version="0.1.0",
    description="CKAN site AI assistant integration",
    long_description="CKAN extension that adds an AI assistant panel and proxies requests to an external assistant service.",
    classifiers=[],
    author="",
    license="AGPLv3",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "requests>=2.28",
    ],
    entry_points="""
        [ckan.plugins]
        assistant=ckanext.assistant.plugin:AssistantPlugin
    """,
)
