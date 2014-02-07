from setuptools import setup


setup(
    name='tangled.web',
    version='0.1a4.dev0',
    description='RESTful Web Framework',
    long_description=open('README.rst').read(),
    url='http://tangledframework.org/',
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
    install_requires=[
        'tangled>=0.1.dev0',
        'MarkupSafe>=0.18',
        'venusian>=1.0a8',
        'WebOb>=1.3.1',
        'zc.recipe.egg',
    ],
    extras_require={
        'dev': [
            'tangled[dev]',
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
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
