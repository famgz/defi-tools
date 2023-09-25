from setuptools import setup, find_packages

with open('requirements.txt') as f:
    REQUIREMENTS = f.readlines()

setup(
    name='defi_tools',
    version='0.1',
    license='MIT',
    author="famgz",
    author_email='famgz@proton.me',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    url='https://github.com/famgz/defi_tools',
    install_requires=REQUIREMENTS
)
