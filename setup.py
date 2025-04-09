from setuptools import setup, find_packages

setup(
    name="control-panel",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0.0",
        "tabulate>=0.8.9",
        "flask>=2.0.0,<2.2.0",  # Flask 2.2+ has issues with werkzeug compatibility
        "werkzeug>=2.0.0,<2.1.0",  # Pin werkzeug to a compatible version
    ],
    entry_points={
        "console_scripts": [
            "panel=control_panel.cli:main",
        ],
    },
    python_requires=">=3.6",
)
