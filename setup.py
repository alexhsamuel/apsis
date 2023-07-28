from   pathlib import Path
import setuptools
import sys

with (Path(sys.argv[0]).parent / "README.md").open("rt") as file:
    long_description = file.read()

setuptools.setup(
    name            ="apsis",
    version         ="0.17.5",
    description     ="Easy-to-use task scheduler",
    long_description=long_description,
    url             ="https://github.com/alexhsamuel/apsis",
    author          ="Alex Samuel",
    author_email    ="alex@alexsamuel.net",
    license         ="MIT",
    keywords        =["scheduler"],
    classifiers     =[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.9",
    ],

    install_requires=[
        "brotli",
        "jinja2",
        "ora",
        "pyyaml",
        "requests",
        "rich",
        "sanic >=21.3",
        "sqlalchemy <2",
        "ujson",
    ],

    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
        ],
    },

    package_dir     ={"": "python"},
    packages        =[
        "apsis",
        "apsis.agent",
        "apsis.cond",
        "apsis.lib",
        "apsis.lib.itr",
        "apsis.program",
        "apsis.program.internal",
        "apsis.schedule",
        "apsis.service",
    ],
    package_data    ={
        "": ["test/*"],
        "apsis.agent": [
            "agent.cert",
            "agent.key",
        ],
        "apsis.service": [
            "vue/*",
            "vue/static/css/*",
            "vue/static/js/*",
            "vue/static/fonts/*",
        ],
    },
    entry_points    ={},
    scripts         =[
        "bin/apsis",
        "bin/apsisctl",
        "bin/apsis-agent",
    ],
)

