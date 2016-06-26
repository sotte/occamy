from setuptools import setup

setup(name='occamy',
      version='0.2',
      description='Phoenix channel client for Python',
      url='http://github.com/BossaNova/occamy',
      author='Joe Hosteny',
      author_email='joe@bnrobotics.com',
      license='MIT',
      packages=['occamy'],
      install_requires=[
          'ws4py'
      ],
      zip_safe=False)
