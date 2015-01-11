from setuptools import setup


setup(name='glreg',
      version='0.9.0a3',
      description='OpenGL XML API registry parser',
      long_description=open('README.rst').read(),
      url='https://github.com/pyokagan/pyglreg',
      author='Paul Tan',
      author_email='pyokagan@gmail.com',
      license='MIT',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Topic :: Software Development :: Code Generators',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      keywords='opengl',
      py_modules=['glreg'],
      entry_points={
          'console_scripts': [
              'glreg=glreg:main'
          ]
      })
