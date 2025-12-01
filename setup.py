from setuptools import setup, find_packages

setup(
    name="chaos-sdk",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[],
    extras_require={
        "dev": ["pytest", "pytest-asyncio", "black", "isort"],
    },
    python_requires=">=3.10",
)
