"""Setup configuration for TLPH Inventory Management System."""

from setuptools import setup, find_packages
import os

# Read version from __version__.py
version_dict = {}
with open(os.path.join(os.path.dirname(__file__), '__version__.py')) as f:
    exec(f.read(), version_dict)

# Read long description from README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='tlph-inventory',
    version=version_dict['__version__'],
    author=version_dict['__author__'],
    description=version_dict['__description__'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alqzdave/TLPH',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Framework :: Flask',
    ],
    entry_points={
        'console_scripts': [
            'tlph=app:main',
        ],
    },
)
