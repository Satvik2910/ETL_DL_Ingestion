"""Setup script for Driver Insight Agent."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="driver-insight-agent",
    version="1.0.0",
    author="Driver Insight Team",
    author_email="team@driverinsight.com",
    description="A modular agent responsible for fetching and managing driver data efficiently from external APIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/driver-insight-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-httpx>=0.26.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
        "redis": [
            "redis>=5.0.1",
        ],
        "production": [
            "gunicorn>=21.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "driver-insight-agent=driver_insight_agent.app:run_server",
        ],
    },
    include_package_data=True,
    package_data={
        "driver_insight_agent": ["config/*.yaml"],
    },
)