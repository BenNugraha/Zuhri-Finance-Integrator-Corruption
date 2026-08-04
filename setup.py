"""
ZFIC V3 - Setup File
Instalasi package zfic untuk development dan deployment.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zfic",
    version="3.0.0",
    author="Benny Nugraha, A.md (Abu Syifa al Bantani)",
    author_email="arsitek@zfic.id",
    description="Zuhri Financial Integrity Core — Anti-korupsi berbasis matematika presisi",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/[username]/zfic-v3",
    packages=find_packages(),  # otomatis temukan folder zfic/
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "flask>=2.0.0",
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "requests>=2.25.0",
        "pytest>=7.0.0",
        "mpmath>=1.3.0",   # untuk presisi 61 digit
    ],
    extras_require={
        "dev": ["pytest", "black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "zfic-server=app:main",  # opsional: jalankan server dengan perintah `zfic-server`
        ],
    },
    include_package_data=True,
    zip_safe=False,
)