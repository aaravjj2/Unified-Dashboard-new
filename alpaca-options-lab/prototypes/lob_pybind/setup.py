from setuptools import setup, Extension
import sys

try:
    import pybind11
    include_dirs=[pybind11.get_include()]
except Exception:
    include_dirs=[]

ext_modules = [
    Extension(
        'lob_proto',
        ['lob.cpp'],
        include_dirs=include_dirs,
        language='c++'
    )
]

setup(
    name='lob_proto',
    ext_modules=ext_modules,
)
