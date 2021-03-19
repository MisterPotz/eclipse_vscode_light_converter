
from pathlib import Path
from typing import List, Set
import zipfile
import re
import json
from json import dump, load, loads, JSONDecodeError

manifest_path = "META-INF/MANIFEST.MF"
p2_info_path = "META-INF/p2.inf"
dependency_declaration_keyword = "Require-Bundle"
dependency_declaration_word_end = ":"
classpath_file_subpath = ".classpath"
settings_file_subpath = ".settings/org.eclipse.jdt.core.prefs"
settings_magic_line_pattern = re.compile(r".*org\.eclipse\.jdt\.core\.compiler\.problem\.forbiddenReference[\s]*=[\s]*ignore.*")
settings_magic_line = "org.eclipse.jdt.core.compiler.problem.forbiddenReference=ignore"
classpath_autogen_line_pattern = re.compile(r".*<!-- BELOW AUTO GEN -->.*")
vscode_settings_folder = ".vscode/"
vscode_settings_subpath = ".vscode/settings.json"
vscode_settings = { "java.import.maven.enabled": False, "java.autobuild.enabled": False}

def flat_map(f, xs):
    ys = []
    for x in xs:
        ys.extend(f(x))
    return ys

def pretty_print_header(adict, lengths=False):
    for key, value in adict.items():
        print(key, end='\t')
        if (lengths):
            print(f"length: {len(value)}")
        else:
            print()
        for i in value:
            print(i)
    print()

def pretty_print(arr):
    if isinstance(arr, set):
        arr = list(arr)
    for i in range(0, len(arr)):
        if i == 0:
            print("[")
        print(f"\t{arr[i]}", end="")
        if i == len(arr) - 1:
            print()
            print("]")
        else:
            print(",")

class Dependency:
    def __init__(self, dependency_manifest_string, is_p2_required_line=False):
        params = dependency_manifest_string.split(';')
        self.name = params[0].strip()
        self.exported = dependency_manifest_string.find(
            "reexport") > 0 or is_p2_required_line

    @classmethod
    def from_file_string(cls, file_string: str):
        cls.name = file_string
        # True because cached dependency means its exported
        cls.exported = True

    def to_bundle(self, p2_rep: Path):
        return Bundle(p2_rep, self.name)

    def __str__(self):
        return f"{self.name} : exported {int(self.exported)}"

    def __repr__(self):
        return f"{self.name}"
class Project():
    def __init__(self, root: str, module_root: str = None):
        self.root = root
        self.module_root = module_root

    def module_path(self):
        return Path(self.root).joinpath(self.module_root)

    def list_root(self):
        return Path(self.root).iterdir()

    def is_in_root(self, name):
        pattern = r".*({}).*".format(name)
        found = list(filter(lambda x: re.fullmatch(
            pattern, x.stem + x.suffix), self.list_root()))
        return len(found) > 0

    def get_classpath_file(self):
        return self.module_path().joinpath(classpath_file_subpath)


class Bundle:
    def __init__(self, p2_rep: str, name: str, proj: Project = None, cache_folder: str = None):
        self.p2_rep = Path(p2_rep)
        self.name = name
        self.jars = []
        self.proj = proj
        self.all_pattern = r"({})(\.source)?_[\.a-zA-Z0-9-]+\.jar".format(
            self.name)
        self.header_pattern = r"({})_[\.a-zA-Z0-9-]+\.jar".format(self.name)
        self.dependencies = []
        self.cache_folder = cache_folder
        # print(self.all_pattern, self.header_pattern)

    def is_tycho(self):
        return self.proj is None

    def cache_folder_path(self):
        return Path(self.cache_folder)

    def cache_file(self):
        # etvsc - eclipse to vs code
        return self.cache_folder_path().joinpath(f"{self.name}.etvsc")

    def plugins_path(self):
        return self.p2_rep.joinpath("pool/plugins")

    def to_file_string(self):
        return self.name

    def jars_paths(self):
        plugins = self.plugins_path()
        return list(map(lambda x: plugins.joinpath(x), self.jars))

    def update_jars(self):
        if self.is_tycho() is False:
            print("not tycho")
            return []
        plugins = self.plugins_path()
        bundles = plugins.glob("*.jar")
        bundles = list(bundles)
        jars = list(filter(lambda x: re.fullmatch(
            self.all_pattern, x.stem + x.suffix) is not None, bundles))
        jars = list(map(lambda x: str(x.stem + x.suffix), jars))
        self.jars = jars

    '''Looks for a jar that is named like the given name in the given p2 repository 
    '''
    def get_jar_with_manifest_for_p2(self):
        pattern = re.compile(self.header_pattern)
        if self.jars is None or len(self.jars) == 0:
            return None
        not_source = list(
            filter(lambda x: re.fullmatch(pattern, x), self.jars))
        if self.jars is None or len(not_source) == 0:
            return None
        manifest = self.plugins_path().joinpath(not_source[0])
        if not manifest.exists():
            print("could not update dependencies: manifest path doesn't exist")
            return None
        return manifest

    def get_manifest_file_for_eclipse(self):
        assert self.proj is not None
        path = self.proj.module_path()
        manifest = path.joinpath(manifest_path)
        if not manifest.exists():
            print("could not get manifest file for Eclipse project")
            return None
        return manifest

    def get_manifest_file_lines(self):
        if (self.is_tycho()):
            file = self.get_jar_with_manifest_for_p2()
            if file is None:
                return []
            zip1 = zipfile.ZipFile(file)
            manifest_file = zipfile.Path(zip1).joinpath(manifest_path)
            lines = []
            with manifest_file.open('r') as file:
                lines = file.readlines()
            return list(map(lambda x: x.decode('utf8').rstrip("\n\r"), lines))
        else:
            manifest_file = self.get_manifest_file_for_eclipse()
            with manifest_file.open('r') as file:
                lines = file.readlines()
            return list(map(lambda x: x.strip(), lines))

    def get_p2_info_file_lines(self):
        if (self.is_tycho()):
            file = self.get_jar_with_manifest_for_p2()
            if file is None:
                return []
            zip_jar = zipfile.ZipFile(file)
            p2_file = zipfile.Path(zip_jar).joinpath(p2_info_path)
            lines = []
            if not p2_file.exists():
                return []
            with p2_file.open('r') as file:
                lines = file.readlines()
            return list(map(lambda x: x.decode('utf8').rstrip("\n\r"), lines))
        else:
            return []

    def update_dependencies(self):
        manifest_lines = self.get_manifest_file_lines()
        p2_info_lines = self.get_p2_info_file_lines()
        if len(manifest_lines) != 0:
            dependencies = parse_manifest_file_lines(manifest_lines)
            self.dependencies = dependencies

        if p2_info_lines is not None and len(p2_info_lines) != 0:
            dependencies = parse_p2_info_file_lines(p2_info_lines)
            self.dependencies.extend(dependencies)

    def get_dependencies(self, show_proj_siblings=True):
        if (len(self.dependencies) == 0):
            print("possibly the dependencies are not yet updated")
            return []
        if (show_proj_siblings or (not show_proj_siblings and self.is_tycho())):
            return self.dependencies
        else:
            return list(filter(lambda x: not self.proj.is_in_root(x.name), self.dependencies))

    def __str__(self):
        exported = self.get_exported_dependencies()
        return f"{self.name} | {len(self.jars)} jars | {len(self.dependencies)} deps | {len(exported)} exported"

    def __repr__(self):
        exported = self.get_exported_dependencies()
        return f"{self.name} | {len(self.jars)} jars | {len(self.dependencies)} deps | {len(exported)} exported"

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Bundle):
            return False
        return self.name == o.name

    def __ne__(self, o: object) -> bool:
        return not self == o

    def get_exported_dependencies(self):
        if self.dependencies is None or len(self.dependencies) == 0:
            return []
        return list(filter(lambda x: x.exported, self.dependencies))

    def update_jars_if_must(self):
        if (self.jars is None or len(self.jars) == 0) and self.is_tycho():
            self.update_jars()

    def update_dependencies_if_must(self):
        if self.dependencies is None or len(self.dependencies) == 0:
            self.update_dependencies()

    # collect the whole dependencies hierarchy
    def collect_exported_dependencies(self, clean_cache = False):
        # first must check if cache is present because parsing all dependencies is not a fast process
        exported_dependencies = []
        if not self.is_tycho() and self.has_dependencies_cache_file() and not clean_cache:
            return set(self.collect_exported_dependencies_from_cache())
        else:
            # parse all
            self.update_jars_if_must()
            self.update_dependencies_if_must()
            if self.is_tycho():
                exported_dependencies = self.get_exported_dependencies()
            else:
                # if collecting deps for eclipse project then must collect all, not only exported, and omit sibling projects
                exported_dependencies = list(
                    filter(lambda x: not self.proj.is_in_root(x.name), self.dependencies))
            bundles = list(map(lambda x: x.to_bundle(
                self.p2_rep), exported_dependencies))
            # pretty_print(bundles)
            for i in bundles:
                i.update_jars()
                i.update_dependencies()
            temp_arr = []

            for i in bundles:
                # print(f"dependencies for bundle: {i}")
                i_deps = i.collect_exported_dependencies()
                temp_arr.extend(i_deps)
            this_level_dependencies = set(bundles)
            nested_dependencies = set(temp_arr)
            full_set = list(this_level_dependencies.union(
                list(nested_dependencies)))
            # after all dependencies found, need to filter out those without jars
            full_set = list(
                filter(lambda x: x.jars is not None and len(x.jars) > 0, full_set))
            return set(full_set)

    def check_that_classpath_merged(self) -> bool :
        classpath_file = self.proj.get_classpath_file()
        lines = []
        with classpath_file.open('r') as readable:
            lines = readable.readlines()
        for line in lines:
            # if that line is encountered, the file is merged
            if re.match(classpath_autogen_line_pattern, line) is not None:
                return True
        # not merged
        return False

    def merge_with_classpath(self, clean_cache=False):
        # only if it is eclipse project and classpath is not merged
        if self.is_tycho():
            return
        if self.check_that_classpath_merged():
            print("already converted to code")
            return

        classpath_file = self.proj.get_classpath_file()

        # collect cached or newly parsed dependencies
        dependencies = list(self.collect_exported_dependencies(clean_cache=clean_cache))
        # if no cache - put into cache
        if not self.has_dependencies_cache_file() or clean_cache:
            self.cache_exported_dependencies(dependencies)
        # convert to jars
        dependencies = flat_map(lambda x: x.jars_paths(), dependencies)
        merge_dependencies_with_classpath(classpath_file, dependencies)

    def clean_classpath(self):
        if not self.is_tycho():
            classpath_file = self.proj.get_classpath_file()
            clean_classpath(classpath_file)

    def has_dependencies_cache_file(self, cache_file_given=None):
        cache_file = None
        if cache_file_given is not None:
            cache_file = cache_file_given
        else:
            cache_file = self.cache_file()
        return cache_file.exists() and cache_file.is_file()

    def cache_exported_dependencies(self, exported_dependencies):
        # must delete cache file if exists
        cache_file = self.cache_file()
        if self.has_dependencies_cache_file(cache_file_given=cache_file):
            cache_file.unlink()
        # fetch dependencies
        # exported: List[Dependency] = list(self.collect_exported_dependencies())
        # lines that will be writtent to the cache file
        exported = list(map(lambda x: f"{x.to_file_string()}\n", exported_dependencies))
        with cache_file.open('w') as opened_file:
            opened_file.writelines(exported)
    
    def collect_exported_dependencies_from_cache(self):
        cache_file = self.cache_file()
        lines = []
        with cache_file.open('r') as opened_file:
            lines = opened_file.readlines()
        dependencies = list(map(lambda x: x.replace("\n", ''), lines))
        dependencies = list(filter(lambda x: len(x) != 0, dependencies))
        dependencies = list(map(lambda x: Bundle(self.p2_rep,x), dependencies))
        for bundle in dependencies:
            bundle.update_jars()
        return dependencies

    def add_magic_line_to_settings(self):
        settings_file = self.proj.module_path().joinpath(settings_file_subpath)
        
        if settings_file.exists():
            lines = []
            with settings_file.open('r') as opened_file:
                lines = opened_file.readlines()
            line_is_present = False
            for line in lines:
                if re.match(settings_magic_line_pattern, line) is not None:
                    line_is_present = True
                    break
            if not line_is_present:
                lines.append(f"{settings_magic_line}\n")
                with settings_file.open('w') as writable:
                    writable.writelines(lines)
        else:
            settings_file.touch()
            with settings_file.open('w') as writable:
                lines = [f"{settings_magic_line}\n"]
                writable.writelines(lines)


def split_by_commas(lines):
    parenthesis_stack = []
    new_lines = []
    last_index = 0
    for index, i in enumerate(lines):
        if (i == '"'):
            if (len(parenthesis_stack) > 0):
                parenthesis_stack.pop()
            else:
                parenthesis_stack.append(i)
        elif (i == ','):
            if len(parenthesis_stack) == 0:
                new_lines.append(lines[last_index:index].strip())
                last_index = index + 1
    new_lines.append(lines[last_index:].strip())
    return new_lines


def parse_manifest_file_lines(lines) -> List[Dependency]:
    require_block_declaration_pattern = re.compile(
        r"[\s]*({})[\s]*:[\s]*.*".format(dependency_declaration_keyword))
    block_declaration_pattern = re.compile(r"[a-zA-Z-]*:[\ ]*.*")
    first_match = False
    first_index = 0
    for index, i in enumerate(lines):
        if re.fullmatch(require_block_declaration_pattern, i) is not None:
            first_index = index
            first_match = True
            continue
        if first_match and re.fullmatch(block_declaration_pattern, i) is not None:
            lines = lines[first_index:index]
            break
    # no match found
    if not first_match:
        return []
    lines = list(map(lambda x: x.strip(), lines))
    lines = ''.join(lines)
    lines = lines.strip()[lines.find(dependency_declaration_keyword) +
                          len(dependency_declaration_keyword + dependency_declaration_word_end):]
    lines = split_by_commas(lines)
    # can be case when ',' was inside brackets
    dependencies = list(map(lambda x: Dependency(x.strip()), lines))
    return dependencies


def parse_p2_info_file_lines(lines) -> List[Dependency]:
    requires_pattern = re.compile(
        r"[\s]*(requires)\.[0-9]+\.(name)[\s]*\=[\s]*.*")

    requirements = list(filter(lambda x: re.fullmatch(
        requires_pattern, x) is not None, lines))

    def delete_keywords_part(line: str):
        lines1 = line.split("=")
        line1 = lines1[1].strip()
        return line1
    requirements = list(map(lambda x: delete_keywords_part(x), requirements))
    requirements = list(map(lambda x: Dependency(
        x, is_p2_required_line=True), requirements))
    return requirements


def merge_dependencies_with_classpath(file: Path, dependencies: List[str]):
    lines = []
    with file.open('r+') as opened_file:
        lines = opened_file.readlines()
    with file.open('w+') as opened_file:
        i_lines = enumerate(lines)
        i_lines = list(
            filter(lambda x: x[1].find("</classpath>") >= 0, i_lines))
        index, line = i_lines[0]
        diff = len(lines) - index
        lines.insert(len(lines) - diff, "<!-- BELOW AUTO GEN -->\n")
        for dependency in dependencies:
            line = '<classpathentry exported="true" kind="lib" path="{}"/>\n'
            line = line.format(dependency)
            lines.insert(len(lines) - diff, line)
        opened_file.writelines(lines)


def clean_classpath(file: Path):
    lines = []
    with file.open('r+') as opened_file:
        lines = opened_file.readlines()
    generation_start_index = -1
    generation_end_index = -1
    end_pattern = re.compile(r".*</classpath>.*")
    machine_pattern = classpath_autogen_line_pattern
    for index, line in enumerate(lines):
        if re.match(machine_pattern, line.strip()):
            generation_start_index = index
        if (re.match(end_pattern, line.strip())):
            generation_end_index = index
    # don't clean the file if no special lines were found
    if generation_start_index == -1:
        print("already converted to eclipse")
        return
    first_part = lines[:generation_start_index]
    end_part = lines[generation_end_index:]
    first_part.extend(end_part)
    with file.open('w+') as opened_file:
        opened_file.writelines(first_part)
    
def configure_vs_code_settings(project_path: Path):
    dir = project_path.joinpath(vscode_settings_folder)
    if not dir.exists():
        dir.mkdir()
    file = project_path.joinpath(vscode_settings_subpath)
    jobj = json.loads("{ }")
    if file.exists():
        try:
            with file.open('r') as opened_file:
                jobj = json.load(opened_file)
        except JSONDecodeError:
            pass
    else:
        file.touch()
    for key, value in zip(vscode_settings.keys(), vscode_settings.values()):
        if (key not in jobj):
            jobj[key] = value
    with file.open('w') as writable:
        dump(jobj, writable, indent=4)
    

test_deps = """
Require-Bundle: org.eclipse.emf.ecore.xmi;bundle-version="2.16.0";visi
 bility:=reexport,org.eclipse.emf.ecore;bundle-version="2.20.0";visibi
 lity:=reexport,org.eclipse.emf.common;bundle-version="2.17.0",org.ant
 lr.runtime;bundle-version="[3.2.0,3.2.1)";visibility:=reexport,com.go
 ogle.inject;bundle-version="3.0.0";visibility:=reexport,org.objectweb
 .asm;bundle-version="[8.0.1,8.1.0)";resolution:=optional,org.eclipse.
 emf.mwe.core;bundle-version="1.3.21";resolution:=optional;visibility:
 =reexport,org.eclipse.emf.mwe.utils;bundle-version="1.3.21";resolutio
 n:=optional;visibility:=reexport,org.eclipse.xtend;bundle-version="2.
 2.0";resolution:=optional,org.eclipse.xtend.typesystem.emf;bundle-ver
 sion="2.2.0";resolution:=optional,org.eclipse.xtext.util;visibility:=
 reexport,org.eclipse.core.runtime;bundle-version="3.13.0";resolution:
 =optional;x-installation:=greedy,org.eclipse.xtend.lib;resolution:=op
 tional,org.eclipse.equinox.common;bundle-version="3.9.0"
Bundle-ManifestVersion: 2
""".split("\n")


test_deps1 = """
Manifest-Version: 1.0
Automatic-Module-Name: org.eclipse.swt
Bundle-SymbolicName: org.eclipse.swt; singleton:=true
Bundle-ManifestVersion: 2
Bundle-RequiredExecutionEnvironment: JavaSE-1.8
Eclipse-SourceReferences: scm:git:git://git.eclipse.org/gitroot/platfo
 rm/eclipse.platform.swt.git;path="bundles/org.eclipse.swt";tag="I2020
 0831-0600";commitId=e17fs8602defb4c167e3c86b836448daea6cab383
Bundle-Vendor: %providerName
DynamicImport-Package: org.eclipse.swt.accessibility2
Eclipse-ExtensibleAPI: true
Export-Package: org.eclipse.swt,org.eclipse.swt.accessibility,org.ecli
 pse.swt.awt,org.eclipse.swt.browser,org.eclipse.swt.custom,org.eclips
 e.swt.dnd,org.eclipse.swt.events,org.eclipse.swt.graphics,org.eclipse
 .swt.layout,org.eclipse.swt.opengl,org.eclipse.swt.printing,org.eclip
 se.swt.program,org.eclipse.swt.widgets,org.eclipse.swt.internal; x-fr
 iends:="org.eclipse.ui",org.eclipse.swt.internal.image; x-internal:=t
 rue
Bundle-Name: %pluginName
Bundle-Version: 3.115.0.v20200831-1002
Bundle-Localization: plugin
Build-Jdk-Spec: 11
Created-By: Maven Archiver 3.5.0

Name: META-INF/p2.inf
"""

test_dep_p2 = """
requires.1.namespace=java.package
requires.1.name=org.eclipse.swt.accessibility2
requires.1.optional=true
requires.1.greedy=false
requires.1.range=0.0.0

# ensure that the applicable implementation fragment gets installed (bug 361901)
requires.2.namespace = org.eclipse.equinox.p2.iu
requires.2.name = org.eclipse.swt.win32.win32.x86_64
requires.2.range = [$version$,$version$]
requires.2.filter = (&(osgi.os=win32)(osgi.ws=win32)(osgi.arch=x86_64)(!(org.eclipse.swt.buildtime=true)))

requires.3.namespace = org.eclipse.equinox.p2.iu
requires.3.name = org.eclipse.swt.cocoa.macosx.x86_64
requires.3.range = [$version$,$version$]
requires.3.filter = (&(osgi.os=macosx)(osgi.ws=cocoa)(osgi.arch=x86_64)(!(org.eclipse.swt.buildtime=true)))

requires.4.namespace = org.eclipse.equinox.p2.iu
requires.4.name = org.eclipse.swt.gtk.linux.x86_64
requires.4.range = [$version$,$version$]
requires.4.filter = (&(osgi.os=linux)(osgi.ws=gtk)(osgi.arch=x86_64)(!(org.eclipse.swt.buildtime=true)))

requires.5.namespace = org.eclipse.equinox.p2.iu
requires.5.name = org.eclipse.swt.gtk.linux.ppc64le
requires.5.range = [$version$,$version$]
requires.5.filter = (&(osgi.os=linux)(osgi.ws=gtk)(osgi.arch=ppc64le)(!(org.eclipse.swt.buildtime=true)))

requires.6.namespace = org.eclipse.equinox.p2.iu
requires.6.name = org.eclipse.swt.gtk.linux.aarch64
requires.6.range = [$version$,$version$]
requires.6.filter = (&(osgi.os=linux)(osgi.ws=gtk)(osgi.arch=aarch64)(!(org.eclipse.swt.buildtime=true)))

"""
