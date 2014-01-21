from setuptools import setup, find_packages


setup(
    name='${package_name}',
    version='0.1.dev0',
    packages=find_packages(),
    install_requires=(
        'tangled.web>=${version_tangled_web}',
    ),
)
