import os
import shutil

from setuptools import Command, find_packages, setup


class CopyFiles(Command):
    """Custom command to copy templates and static files into the package directory"""

    description = "Copy templates and static files into the package directory"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # Copy templates
        if os.path.exists("templates"):
            if not os.path.exists("control_panel/templates"):
                os.makedirs("control_panel/templates", exist_ok=True)
            shutil.copytree("templates", "control_panel/templates", dirs_exist_ok=True)
            print("Templates copied to control_panel/templates")

        # Copy static files
        if os.path.exists("static"):
            if not os.path.exists("control_panel/static"):
                os.makedirs("control_panel/static", exist_ok=True)
            shutil.copytree("static", "control_panel/static", dirs_exist_ok=True)
            print("Static files copied to control_panel/static")


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
        "psutil>=5.9.0",  # For system metrics functionality
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
    cmdclass={
        "copy_files": CopyFiles,
    },
)
