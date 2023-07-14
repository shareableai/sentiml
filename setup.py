import sentiml
import pathlib

from setuptools import setup

LOCAL = pathlib.Path(__file__).parent
README = ""#(LOCAL / "README.md").read_text()

try:
    requirements = open("requirements.txt", "r").readlines()
except FileNotFoundError:
    requirements = []

try:
    dev_requirements = open("dev_requirements.txt", "r").readlines()
except FileNotFoundError:
    dev_requirements = []


setup(
    name=sentiml.__name__,
    version=sentiml.__version__,
    description=sentiml.__description__,
    long_description=README,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=["sentiml"],
    requirements=requirements,
    extras_require={"dev": dev_requirements},
)