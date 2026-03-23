from setuptools import find_packages, setup

setup(
    name="gyrodynamo-audacity-bridge",
    version="0.1.0",
    description="Local-only Audacity automation bridge over mod-script-pipe",
    python_requires=">=3.10",
    packages=find_packages(include=["audacity_bridge", "audacity_bridge.*"]),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "audacity-bridge=audacity_bridge.cli:main",
        ]
    },
)
