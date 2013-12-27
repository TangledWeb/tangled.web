from setuptools import setup, find_packages


setup(
    name='tangled.web',
    version='0.1.dev0',
    description='RESTful Web Framework',
    long_description=open('README').read(),
    packages=find_packages(),
    install_requires=(
        'tangled>=0.1.dev0',
        'venusian>=1.0a8',
        'WebOb>=1.3.1',
    ),
    extras_require={
        'dev': (
            'tangled[dev]',
        ),
    },
    entry_points="""
    [tangled.scripts]
    serve = tangled.web.scripts.serve
    shell = tangled.web.scripts.shell
    show = tangled.web.scripts.show

    """,
    classifiers=(
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ),
)
