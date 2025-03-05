# ipywwt

## Installation

```sh
pip install ipywwt
```

## Development

In your development environment, install the package in editable mode:

```sh
pip install -e .
```

The widget front-end code bundles it's JavaScript dependencies. After setting up Python,
make sure to install these dependencies locally:

```sh
npm install
```

## Example usage

Open `Widget.ipynb` in JupyterLab, VS Code, or your favorite editor to see an 
example of how to use the widget.

The widget also works with Solara. To see an example of how to use the widget 
in Solara, run the following commands:

```sh
pip install solara
solara run notebooks/solara_test.py
```
