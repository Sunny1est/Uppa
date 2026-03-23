"""
setup.py - Setup do Uppa!

Para instalar em modo desenvolvimento:
    pip install -e .

Para criar distribuição:
    python setup.py bdist_wheel
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="uppa",
    version="0.2.8",
    author="Seu Nome",
    author_email="seu.email@example.com",
    description="Um mascote de produtividade gamificado - Uppa!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/seu-usuario/uppa",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.8",
    install_requires=[
        "customtkinter==5.2.2",
        "pillow==12.1.0",
        "darkdetect==0.8.0",
        "pywin32==311",
    ],
    entry_points={
        "gui_scripts": [
            "uppa=main:main",
        ],
    },
    include_package_data=True,
)
