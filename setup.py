from setuptools import setup, Extension, find_namespace_packages
from setuptools.command.build_ext import build_ext
import subprocess
import sys
import os

class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)

class CMakeBuild(build_ext):
    def run(self):
        try:
            _ = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError("CMake must be installed to build the following extensions: " + ", ".join(e.name for e in self.extensions))

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cfg = 'Debug' if self.debug else 'Release'
        cmake_args = [
            '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
            '-DCMAKE_RUNTIME_OUTPUT_DIRECTORY=' + extdir,
            # Multi-configuration generators otherwise append Release/Debug,
            # placing the Windows .pyd outside the package collected by pip.
            '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_' + cfg.upper() + '=' + extdir,
            '-DCMAKE_RUNTIME_OUTPUT_DIRECTORY_' + cfg.upper() + '=' + extdir,
            '-DPython3_EXECUTABLE=' + sys.executable,
            '-DPYBIND11_FINDPYTHON=ON',
            '-DCMAKE_BUILD_TYPE=' + cfg,
        ]
        build_args = ['--config', cfg]
        if self.parallel:
            build_args += ['--parallel', str(self.parallel)]
        elif 'CMAKE_BUILD_PARALLEL_LEVEL' not in os.environ:
            build_args += ['--parallel', '4']

        # Visual Studio defaults to the host architecture. Match the wheel's
        # target instead, while allowing explicitly configured generators.
        generator = os.environ.get('CMAKE_GENERATOR', '')
        if sys.platform == 'win32' and (not generator or 'Visual Studio' in generator):
            if 'CMAKE_GENERATOR_PLATFORM' not in os.environ:
                platform = {'win32': 'Win32', 'win-amd64': 'x64', 'win-arm64': 'ARM64'}
                cmake_args += ['-A', platform[self.plat_name]]

        env = os.environ.copy()
        build_temp = os.path.join(self.build_temp, ext.name)
        os.makedirs(build_temp, exist_ok=True)
        if 'CMAKE_VERBOSE_MAKEFILE' in env:
            cmake_args += ['-DCMAKE_VERBOSE_MAKEFILE=1']
        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args, cwd=build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=build_temp, env=env)


setup(
    ext_modules=[CMakeExtension("ssapy._ssapy")],
    cmdclass={"build_ext": CMakeBuild},
    packages=find_namespace_packages(include=["ssapy", "ssapy.*"]),
    zip_safe=False,
    include_package_data=True,
)
