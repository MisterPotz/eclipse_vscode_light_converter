
from pathlib import Path
from typing import List
import zipfile
import re

manifest_path = "META-INF/MANIFEST.MF"
dependency_declaration_keyword = "Require-Bundle"
dependency_declaration_word_end = ":"
classpath_file_subpath = ".classpath"

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
        print(f"\t{arr[i]}",end="")
        if i == len(arr) - 1:
            print()
            print("]")
        else:
            print(",")

class Dependency:
    def __init__(self, dependency_manifest_string):
        params = dependency_manifest_string.split(';')
        self.name = params[0].strip()
        self.exported = dependency_manifest_string.find("reexport") > 0

    def to_bundle(self, p2_rep: Path):
        return Bundle(p2_rep, self.name)

    def __str__(self):
        return f"{self.name} : exported {int(self.exported)}"

    def __repr__(self):
        return f"{self.name}"
class Project() :
    def __init__(self, root: str, module_root: str = None) :
        self.root = root
        self.module_root = module_root
    def module_path(self):
        return Path(self.root).joinpath(self.module_root)
    def list_root(self):
        return Path(self.root).iterdir()
    def is_in_root(self, name):
        pattern = r".*({}).*".format(name)
        found = list(filter(lambda x : re.fullmatch(pattern, x.stem + x.suffix), self.list_root()))
        return len(found) > 0
    def get_classpath_file(self):
        return self.module_path().joinpath(classpath_file_subpath)

class Bundle:
    def __init__(self, p2_rep: str, name: str, proj : Project = None):
        self.p2_rep = Path(p2_rep)
        self.name = name
        self.jars = []
        self.proj = proj
        self.all_pattern = r"({})(\.source)?_[\.a-zA-Z0-9-]+\.jar".format(
            self.name)
        self.header_pattern = r"({})_[\.a-zA-Z0-9-]+\.jar".format(self.name)
        self.dependencies = []
        # print(self.all_pattern, self.header_pattern)

    def is_tycho(self):
        return self.proj is None

    def plugins_path(self):
        return self.p2_rep.joinpath("pool/plugins")

    def jars_paths(self):
        plugins = self.plugins_path()
        return list(map(lambda x: plugins.joinpath(x), self.jars))

    def update_jars(self):
        if  self.is_tycho() is False:
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
        if len(self.jars) == 0:
            print("could not update dependencies: jars not updated")
            return None
        not_source = list(
            filter(lambda x: re.fullmatch(pattern, x), self.jars))
        if len(not_source) == 0:
            print("could not update depdendencies: no jars found")
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
                print("could not get manifest lines: no manifest found")
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

    def update_dependencies(self):
        manifest_lines = self.get_manifest_file_lines()
        if len(manifest_lines) != 0:
            dependencies = parse_manifest_file_lines(manifest_lines)
            self.dependencies = dependencies

    def get_dependencies(self, show_proj_siblings=True):
        if (len(self.dependencies) == 0): 
            print("possibly the dependencies are not yet updated")
            return []
        if (show_proj_siblings or (not show_proj_siblings and self.is_tycho())):
            return self.dependencies
        else:
            return list(filter(lambda x : not self.proj.is_in_root(x.name), self.dependencies))

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
    def collect_exported_dependencies(self):
        # first parse all 
        self.update_jars_if_must()
        self.update_dependencies_if_must()
        exported_dependencies = []
        if self.is_tycho():
            exported_dependencies = self.get_exported_dependencies()
        else :
            # if collecting deps for eclipse project then must collect all, not only exported, and omit sibling projects
            exported_dependencies = list(filter(lambda x : not self.proj.is_in_root(x.name), self.dependencies))
        bundles = list(map(lambda x: x.to_bundle(self.p2_rep), exported_dependencies))
        # pretty_print(bundles)
        for i in bundles:
            i.update_jars()
            i.update_dependencies()
        temp_arr = []

        for i in bundles:
            # print(f"dependencies for bundle: {i}")
            i_deps = i.collect_exported_dependencies()
            temp_arr.extend(i_deps)
            # print(all_dependencies)
        this_level_dependencies = set(bundles)
        nested_dependencies = set(temp_arr)
        return this_level_dependencies.union(list(nested_dependencies))

    def merge_with_classpath(self):
        if self.is_tycho():
            return
        classpath_file = self.proj.get_classpath_file()
        # if is eclipse project
        dependencies = list(self.collect_exported_dependencies())
        # convert to jars
        dependencies = flat_map(lambda x: x.jars_paths(), dependencies)
        merge_dependencies_with_classpath(classpath_file, dependencies)

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
        r"({})*:[\ ]*.*".format(dependency_declaration_keyword))
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
    lines = list(map(lambda x: x.strip(), lines))
    lines = ''.join(lines)
    lines = lines.strip()[lines.find(dependency_declaration_keyword) +
                          len(dependency_declaration_keyword + dependency_declaration_word_end):]
    lines = split_by_commas(lines)
    # can be case when ',' was inside brackets
    dependencies = list(map(lambda x: Dependency(x.strip()), lines))
    return dependencies

def merge_dependencies_with_classpath(file: Path, dependencies: List[str]):
    lines = []
    with file.open('r+') as opened_file:
        lines = opened_file.readlines()
    print(file, lines)
    with file.open('w+') as opened_file:
        i_lines = enumerate(lines)
        i_lines = list(filter(lambda x: x[1].find("</classpath>") >= 0, i_lines))
        index, line = i_lines[0]
        diff = len(lines) - index
        lines.insert(len(lines) - diff, "<!-- BELOW AUTO GEN -->\n")
        for dependency in dependencies:
            line = '<classpathentry exported="true" kind="lib" path="{}"/>\n'
            line = line.format(dependency)
            lines.insert(len(lines) - diff, line)
        opened_file.writelines(lines)           

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
