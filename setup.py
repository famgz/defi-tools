from setuptools import setup, find_packages

with open('requirements.txt') as f:
    REQUIREMENTS = f.readlines()

setup(
    name='defi_tools',
    version='0.1',
    license='MIT',
    author="famgz",
    author_email='famgz@proton.me',
    packages=['defi_tools'],
    package_dir={'defi_tools': 'src/defi_tools'},
    include_package_data=True,
    url='https://github.com/famgz/defi-tools',
    install_requires=REQUIREMENTS
)
