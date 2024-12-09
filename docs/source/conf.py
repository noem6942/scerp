# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

# -- Usage to compile -----------------------------------------------------
# sphinx-build -b html docs/source docs/build/html

# start project
project = 'SC-ERP'
copyright = '2024'
author = 'M. Bischof'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',  # Use myst_parser for Markdown parsing
    'sphinx_markdown_tables',  # Optional, for better Markdown table support
]


# Optionally, customize the theme's logo or appearance:
# html_logo = "_static/logo.png"  # Path to a custom logo
# html_favicon = "_static/favicon.ico"  # Path to a custom favicon


templates_path = ['_templates']
exclude_patterns = []

language = 'de'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# Set the theme to "sphinx_rtd_theme"
html_theme = "sphinx_rtd_theme"  # 'alabaster'
html_static_path = ['_static']

# Specify that markdown files should be processed
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Disable the "View Source" button
html_show_sourcelink = False

# Disable the "Created with Sphinx" footer
html_show_sphinx = False
