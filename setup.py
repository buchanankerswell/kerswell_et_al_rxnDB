from setuptools import setup, find_packages

setup(
    name="rxnDB",
    version="0.1.0",
    description="A Python Shiny app for reaction database management.",
    author="Buchanan Kerswell",
    author_email="buck.kerswell@gmail.com",
    url="https://github.com/buchanankerswell/kerswell_et_al_rxnDB",
    packages=find_packages(),
    install_requires=[
        "shiny",
        "pandas",
        "seaborn",
        "faicons",
        "pytest"
    ],
    python_requires=">=3.13",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
