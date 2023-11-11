from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches, chdir, copy, rmdir
from conan.tools.layout import basic_layout
from conan.tools.scm import Version
from conan.errors import ConanInvalidConfiguration
import os

from conans import AutoToolsBuildEnvironment

required_conan_version = ">=1.33.0"

class TinyAlsaConan(ConanFile):
    name = "tinyalsa"
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/tinyalsa/tinyalsa"
    topics = ("tiny", "alsa", "sound", "audio", "tinyalsa")
    description = "A small library to interface with ALSA in the Linux kernel"
    options = {"shared": [True, False], "with_utils": [True, False]}
    default_options = {'shared': False, 'with_utils': False}
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("{} only works for Linux.".format(self.name))

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
    
    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        with chdir(self, self.source_folder):
            env_build = AutoToolsBuildEnvironment(self)
            env_build.make()

    def package(self):
        copy(self, "NOTICE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

        with chdir(self, self.source_folder):
            env_build = AutoToolsBuildEnvironment(self)
            env_build_vars = env_build.vars
            env_build_vars['PREFIX'] = self.package_folder
            env_build.install(vars=env_build_vars)

        rmdir(self, os.path.join(self.package_folder, "share"))

        if not self.options.with_utils:
            rmdir(self, os.path.join(self.package_folder, "bin"))

        with chdir(self, os.path.join(self.package_folder, "lib")):
            files = os.listdir()
            for f in files:
                if (self.options.shared and f.endswith(".a")) or (not self.options.shared and not f.endswith(".a")):
                    os.unlink(f)

    def package_info(self):
        self.cpp_info.libs = ["tinyalsa"]
        if Version(self.version) >= "2.0.0":
            self.cpp_info.system_libs.append("dl")
        if self.options.with_utils:
            bin_path = os.path.join(self.package_folder, "bin")
            self.output.info('Appending PATH environment variable: %s' % bin_path)
            self.env_info.path.append(bin_path)
