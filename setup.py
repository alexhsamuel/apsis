from   pathlib import Path
import setuptools
import sys

with (Path(sys.argv[0]).parent / "README.md").open("rt") as file:
    long_description = file.read()

setuptools.setup(
    name            ="apsis",
    version         ="0.0.0",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],

    install_requires=[
        "fixfmt",
        "jinja2",
        "ora",
        "pyyaml",
        "requests",
        "sanic",
        "sqlalchemy",
        "ujson",
    ],

    package_dir     ={"": "python"},
    packages        =[
        "apsis", 
        "apsis.agent", 
        "apsis.lib", 
        "apsis.lib.itr", 
        "apsis.service",
    ],
    package_data    ={"": ["test/*"]},
    data_files      =[],
    entry_points    ={},
    scripts         =[
        "bin/apsis",
    ],
)

