from setuptools import setup


setup(
    name='${package_name}',
    version='0.1.dev0',
    author='${author}',
    author_email='${author}@example.com',
    url='http://example.com/',
    packages=[
        '${package_name}',
        '${package_name}.tests',
    ],
    install_requires=(
        'tangled.web>=${version_tangled_web}',
    ),
)
