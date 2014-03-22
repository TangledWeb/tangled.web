from setuptools import setup


setup(
    name='tangled.web',
    version='0.1a8',
    description='RESTful Web Framework',
    long_description=open('README.rst').read(),
    url='http://tangledframework.org/',
    download_url='https://github.com/TangledWeb/tangled.web/tags',
    author='Wyatt Baldwin',
    author_email='self@wyattbaldwin.com',
    packages=[
        'tangled',
        'tangled.web',
        'tangled.web.resource',
        'tangled.web.scaffolds',
        'tangled.web.scripts',
        'tangled.web.tests'
    ],
    include_package_data=True,
    install_requires=[
        'tangled>=0.1a7',
        'MarkupSafe>=0.18',
        'venusian>=1.0a8',
        'WebOb>=1.3.1',
        'zc.recipe.egg>=2.0.1',
    ],
    extras_require={
        'dev': [
            'tangled[dev]>=0.1a7',
        ],
    },
    entry_points="""
    [tangled.scripts]
    serve = tangled.web.scripts.serve
    shell = tangled.web.scripts.shell
    show = tangled.web.scripts.show

    [tangled.scaffolds]
    basic = tangled.web.scaffolds:basic

    [zc.buildout]
    wsgi_application = tangled.web.recipes:WSGIApplication

    """,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
)
