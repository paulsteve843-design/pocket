from setuptools import setup, find_packages

setup(
    name="audio-drama-cinema",
    version="1.0.0",
    description="Convert audio dramas into cinematic video productions",
    author="Production Pipeline",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        line.strip() for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    entry_points={
        "console_scripts": [
            "a2c=run_pipeline:main",
        ],
    },
)
