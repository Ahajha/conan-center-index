from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import get, replace_in_file, rmdir
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc
import os


required_conan_version = ">=1.54.0"

class PackageConan(ConanFile):
    name = "git"
    description = "Fast, scalable, distributed revision control system"
    license = "GPL-2.0-only"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://git-scm.com/"
    topics = ("scm", "version-control")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        # C only
        self.settings.compiler.rm_safe("libcxx")
        self.settings.compiler.rm_safe("cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")
    
    def validate(self):
        if cross_building(self):
            raise ConanInvalidConfiguration(f"FIXME: {self.ref} (currently) does not support cross building.")

    def requirements(self):
        self.requires("expat/[>=2.6.2 <3]")
        self.requires("libcurl/[>=7.78.0 <9]")
        self.requires("libiconv/1.17")
        self.requires("openssl/[>=1.1 <4]")
        self.requires("pcre2/10.43")
        self.requires("zlib/[>=1.2.11 <2]")

        # might need perl

    def build_requirements(self):
        self.tool_requires("gettext/0.22.5")
        if is_msvc(self):
            self.tool_requires("ninja/1.11.1")
    
    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        # FIXME: Workaround for https://github.com/conan-io/conan/issues/12012
        if is_msvc(self):
            tc.generator = "Ninja"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake_directory = os.path.join(self.source_folder, "contrib", "buildsystems")
        cmake_file = os.path.join(cmake_directory, "CMakeLists.txt")

        # TODO: replace below with patches

        # FIXME: Handling of expat seems to be a little broken.
        replace_in_file(self, cmake_file, "${EXPAT_LIBRARIES}", "expat::expat")
        replace_in_file(self, cmake_file, "if(EXPAT_VERSION_STRING VERSION_LESS_EQUAL 1.2)", "if(FALSE)")

        # For some reason, libpcre2 specifically uses pkgconfig within CMake, everything else uses find_package.
        # To avoid extra complexity, just replace with a normal find_package
        replace_in_file(self, cmake_file, "find_package(PkgConfig)", "")
        replace_in_file(self, cmake_file, "if(PkgConfig_FOUND)", "if(TRUE)")
        replace_in_file(self, cmake_file, "pkg_check_modules(PCRE2 libpcre2-8)", "find_package(PCRE2)")

        cmake = CMake(self)
        cmake.configure(
            build_script_folder=cmake_directory,
            # USE_VCPKG is checked before project(), so it can't be injected from the toolchain.
            cli_args=["-DUSE_VCPKG=OFF"],
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Contains mainly perl scripts an examples, otherwise is actually rather small
        rmdir(self, os.path.join(self.package_folder, "share"))
        # Contains many exectuables which are near duplicates of `git`, presumably with pre-configured command line args.
        # Greatly bloats the package size.
        rmdir(self, os.path.join(self.package_folder, "libexec"))
        # Only the executables in `bin` seem to be executables normally installed, at least on Ubuntu 22.04 with apt.

    def package_id(self):
        # Just an application
        del self.info.settings.compiler

    def package_info(self):
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
