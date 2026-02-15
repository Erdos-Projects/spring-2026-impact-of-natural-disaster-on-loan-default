# spring-2026-impact-of-natural-disaster-on-loan-default
Team project: spring-2026-impact-of-natural-disaster-on-loan-default

## Usage

This repo is the working codebase for the climate science project.

Datasets should be put in the `data` directory, and will not be tracked by git.

### Python

Install uv for python package management.
Run `uv venv` which will create a virtual environment in `./.venv/bin/python`.

To start jupyter lab, run `uv run --with jupyter jupyter lab` which will start jupyterlab at http://localhost:8888/lab
To use other tools, such as VSCode built in jupyter extension, you can just select the python kernel at `./.venv/bin/python`.

If you have any issues with the python environment, run `uv sync`.
The environment should have all the data science dependencies.
If you need more, add them to the `dependencies` array at `pyproject.toml` file.

If you want to enter the virtual environment, run `source ./.venv/bin/activate`

### Development

- Always work in your own branch
- Don't commit to main unless agreed upon
