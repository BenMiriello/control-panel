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
        "psutil>=5.9.0",          # For system metrics functionality
    ],
    entry_points={
        "console_scripts": [
            "panel=control_panel.cli:main",
            "panel-web=control_panel.web_ui:main",  # Add web UI as separate entry point
        ],
    },
    python_requires=">=3.6",
    description="A central management system for services, ports, and startup configurations on Linux",
    author="BenMiriello",
    author_email="benmiriello@gmail.com",
    url="https://github.com/BenMiriello/control-panel",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Systems Administration",
    ],
)
