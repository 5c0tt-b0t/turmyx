from setuptools import setup

setup(
    name='turmyx',
    version='0.0.3',
    py_modules=['turmyx'],
    install_requires=[
        'Click',
        'configparser'
    ],
    entry_points='''
        [console_scripts]
        turmyx=turmyx:cli
        turmyx-url-opener=turmyx:opener
        turmyx-file-editor=turmyx:editor
    ''',
)
