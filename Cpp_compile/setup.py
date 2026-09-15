import os
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

# Ensure this path points to your actual blender-main source folder
BLENDER_BASE = r"C:\Users\Just\Documents\cpp_bind\blender-main\blender-main"

ext_modules = [
    Pybind11Extension(
        "my_engine",
        ["my_engine.cpp"],
        include_dirs=[
            os.path.join(BLENDER_BASE, r"source\blender\makesdna"),
            os.path.join(BLENDER_BASE, r"intern\guardedalloc"),
            os.path.join(BLENDER_BASE, r"source\blender\blenlib"),
        ],
        cxx_std=17,
        extra_compile_args=["/O2", "/std:c++17"],
    ),
]

setup(
    name="my_engine",
    version="1.0.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)