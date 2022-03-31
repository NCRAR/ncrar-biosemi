from pathlib import Path
from setuptools import find_packages, setup


requirements = [
    'ncrar-audio',
    'pyactivetwo',
    'psiexperiment',
    'websockets',
]


# Get version number
version_file = Path(__file__).parent / 'ncrar_biosemi' / '__init__.py'
for line in version_file.open():
    if line.strip().startswith('__version__'):
        version = line.split('=')[1].strip().strip('\'')
        break
else:
    raise RuntimeError('Could not determine version')


setup(
    name='ncrar-biosemi',
    author='Brad Buran',
    author_email='info@bradburan.com',
    install_requires=requirements,
    packages=find_packages(),
    include_package_data=True,
    description='NCRAR biosemi tools',
    entry_points={
        'console_scripts': [
            'ncrar-nback=ncrar_biosemi.main:main_nback',
        ],
    },
)
