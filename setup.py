from setuptools import setup, find_packages

setup(
    name="control-panel",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
        "pyyaml",
        "tabulate",
        "flask",
    ],
    entry_points={
        "console_scripts": [
            "panel=control_panel.cli:main",
        ],
    },
    python_requires=">=3.6",
)
