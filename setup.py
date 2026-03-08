from setuptools import setup

setup(
    name="diggdeeep",
    version="1.0",
    py_modules=["diggdeeep"],
    entry_points={
        "console_scripts": [
            "diggdeeep=diggdeeep:main"
        ]
    }
)
