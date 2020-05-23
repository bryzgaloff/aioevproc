import setuptools

with open('README.md') as readme_file:
    long_description = readme_file.read()

setuptools.setup(
    name='aioevproc',
    version='0.1.0',
    author='Anton Bryzgalov',
    author_email='tony.bryzgaloff@gmail.com',
    description='Minimal async/sync event processing framework on pure Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/bryzgaloff/aioevproc',
    packages=['aioevproc'],
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
