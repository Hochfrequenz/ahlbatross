<img src="https://raw.githubusercontent.com/Hochfrequenz/ahlbatross/main/ahlbatross.png" alt="ahlbatross.png">

# AHlBatross

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?labelColor=30363D&color=fccccc)](LICENSE)
![Python Versions (officially) supported](https://img.shields.io/pypi/pyversions/ahlbatross.svg)
![Pypi status badge](https://img.shields.io/pypi/v/ahlbatross)
![Unittests status badge](https://github.com/Hochfrequenz/ahlbatross/workflows/Unittests/badge.svg)
![Coverage status badge](https://github.com/Hochfrequenz/ahlbatross/workflows/Coverage/badge.svg)
![Pylint status badge](https://github.com/Hochfrequenz/ahlbatross/workflows/Linting/badge.svg)
![Formatting status badge](https://github.com/Hochfrequenz/ahlbatross/workflows/Formatting/badge.svg)

Tool for **automatic AHB comparison** of consecutive `Formatversionen` provided by 
[machine-readable-anwendungshandbücher](https://github.com/Hochfrequenz/machine-readable_anwendungshandbuecher/).<br>
Highlighted changes between `PruefIDs` of various `Nachrichtenformate` are stored in the `.xlsx` files located inside 
the `./data/output/` [directory](https://github.com/Hochfrequenz/ahlbatross/tree/main/data/output).

<img width="75%" src="https://raw.githubusercontent.com/Hochfrequenz/ahlbatross/main/output.png" alt="output.png">

## Installation
Install it from [PyPI](https://pypi.org/project/ahlbatross/):

```shell
pip install ahlbatross
```

## Development setup

To set up the python development environment, install the required dependencies via

```shell
$ tox -e dev
```

For local testing and code quality maintenance, run 

```shell
tox
```

Check out our [Python Template Repository](https://github.com/Hochfrequenz/python_template_repository#how-to-use-this-repository-on-your-machine) 
for detailed descriptions and step-by-step instructions.

## Contribute

Feel free to contribute to this project by opening a pull request against the main branch.
