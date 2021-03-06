"""Accepts the following arguments:
1. (necessary) path of the project eclipse
2. (necessary) string with names of submodules split by space

-p2 path to p2 repository
-cc convert eclipse project to the code one
-ce convert code project back to the eclipse one

if -cc is set, -p2 must also be set
if -ce is set, will definitely convert back to eclipse format
by default -cc is true so p2 must also be given if no -ce is encounterd

"""
from functools import reduce  # python 3
import operator
from pathlib import Path, PurePosixPath
import sys
import re
from typing import Dict, List, Set
from os import sep
import argparse
import zipfile
import dependency
import parsers

DEBUG = True
# CONSTS
classpath_file_subpath = ".classpath"
dependency_declaration_subpath = "META-INF/MANIFEST.MF"


parser = argparse.ArgumentParser()

parser.add_argument('eclipse_project_path', help='Eclipse project path')
parser.add_argument('submodules_paths',
                    help="Eclipse project submodules paths which are relative to the given root", type=str)
parser.add_argument("-p2", "--p2repository", dest="p2",
                    help="Path to local p2 repository")
parser.add_argument("-cc", "--convert_to_code", dest="to_code",
                    help="Convert given eclipse project to code", action="store_const", const=True, default=True)
parser.add_argument("-ce", "--convert_to_eclipse", dest="to_eclipse",
                    help="Convert given 'coded' ex-eclipse project back to eclipse", action="store_const", const=True, default=False)
args = parser.parse_args()

to_code = args.to_code and not args.to_eclipse

print("eclipse project path {} \n submodules relative paths {} \n p2 repository path {} \n will convert to code {}".format(
    args.eclipse_project_path,
    args.submodules_paths,
    args.p2,
    to_code
))
assert to_code and args.p2 is not None, "Tried to convert to code format but no path to p2 repository was given"

# PREPARE THE INPUT
eclipse_project_path = args.eclipse_project_path
submodules_relative_paths = args.submodules_paths.strip().split()
submodules_relative_paths = list(
    map(lambda x: x.strip(), submodules_relative_paths))

print(submodules_relative_paths)

# MAIN CODE

'''
dependency -> exported dependencies
'''

def paths_for_submodules(project_root: Path, submodules: List[str]):
    return list(map(lambda x: Path(f"{project_root}/{x}"), submodules))

def parse_dependencies_for_submodules(project_root: Path, submodules: List[str]) -> Dict[str, List[str]]:
    paths = paths_for_submodules(project_root, submodules)
    modules_dependencies: Dict[str, List[str]] = {}

    for i in paths:
        dependency_file = i.joinpath(dependency_declaration_subpath)
        lines = []
        with dependency_file.open('r') as file:
            lines = file.readlines()
        i_dependencies = parsers.parse_manifest_file_lines(lines)
        modules_dependencies[str(i)] = i_dependencies

    return modules_dependencies

'''Accepts merged list of dependencies
'''
def map_dependencies_to_p2_repository(module_dependencies: List[str], p2_repository: Path) -> Dict[str, List[str]]:
    set_of_all_deps = module_dependencies
    plugins_path = p2_repository.joinpath("pool/plugins")
    all_files_iterator = plugins_path.glob(r"*.jar")
    dependency_paths: Dict[str, List[str]] = {}
    for i in all_files_iterator:
        for g in set_of_all_deps:
            if (str(i).find(g) >= 0):
                # a match, must save
                if (g not in dependency_paths):
                    dependency_paths[g] = []
                dependency_paths[g].append(str(i))
    return dependency_paths

def dependency_base_name(dependency: str): 
    if (dependency.find("source") > 0):
        return dependency[:dependency.find(".source")]
    else:
        return dependency[:dependency.rfind("_")]

def leave_mostly_source_libs(mapped_dependencies: Dict[str, List[str]]):
    new_dependencies = {}
    for key, value in mapped_dependencies.items():
        value_copy = value.copy()
        only_with_source = list(
            filter(lambda x: x.find("source") > 0, value_copy))
        only_without_source = set(
            filter(lambda x: x.find("source") < 0, value_copy))
        for i in only_with_source:
            base_name = dependency_base_name(i)
            for g in list(only_without_source):
                if (g.startswith(base_name)):
                    # if the same non-source lib is encountered, wipe it out from non-sources array, it is not necessary
                    only_without_source.remove(g)
        # if some libraries in non-sources are still left there, it means that no sources for them were found and they should be appended to deps
        # if (DEBUG):
        #     only_with_source = list(
        #         map(lambda x: x[len("/home/algor/.p2/pool/plugins/"):], only_with_source))
        new_value = [only_with_source, list(only_without_source)]
        new_dependencies[key] = list(reduce(operator.concat, new_value))
    return new_dependencies

def leave_only_latest_versions(mapped_dependencies: Dict[str, List[str]]):
    new_dependencies = {}
    def is_in_set(dependency: str):
        for i in new_dependencies:
            if (dependency_base_name(i) == dependency_base_name(dependency)):
                return (True, i)
        return (False, None)
    def version_of_dependency(dependency: str):
        return dependency[dependency.rfind("_") + 1:]

    for key, value in mapped_dependencies.items():
        dependencies_set = set()
        for i in value:
            in_set, dep_in_set = is_in_set(i)
            # remove dependency with smaller version and add new with the latest version
            if in_set and version_of_dependency(i) > version_of_dependency(dep_in_set):
                dependencies_set.remove(dep_in_set)
                dependencies_set.add(i)
            else:
                dependencies_set.add(i)
        new_dependencies[key] = list(dependencies_set)
    return new_dependencies

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
        for dependency in dependencies:
            line = '<classpathentry exported="true" kind="lib" path="{}"/>\n'
            line = line.format(dependency)
            lines.insert(len(lines) - diff, line)
        opened_file.writelines(lines)           

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
    for i in arr:
        print(i)

def expand_modules_dependencies(modules_dependencies: Dict[str, List[str]], dependency_mapping: Dict[str, List[str]]):
    mapped_module_dependencies = {}
    
    for module, module_dependencies in modules_dependencies.items():
        expanded_module_dependencies = list(filter(lambda x: x in dependency_mapping, module_dependencies))
        expanded_module_dependencies = list(map(lambda x: dependency_mapping[x], expanded_module_dependencies))
        expanded_module_dependencies = list(reduce(operator.concat, expanded_module_dependencies))
        mapped_module_dependencies[module] = expanded_module_dependencies
    return mapped_module_dependencies

def build_dependencies_paths_for_submodules(project_path: Path, submodules_paths: List[Path], p2_path: Path):
    dependencies = parse_dependencies_for_submodules(
        project_path, submodules_paths)
    united_dependencies = reduce(operator.concat, dependencies.values())
    mapped_deps = map_dependencies_to_p2_repository(united_dependencies, p2_path)
    # mapped_deps = leave_mostly_source_libs(mapped_deps)
    mapped_deps = leave_only_latest_versions(mapped_deps)
    return expand_modules_dependencies(dependencies, mapped_deps)

def fill_classpaths_with_deps(moduls_dependencies_mapping: Dict[str, List[str]]):
    for module, module_dependencies in moduls_dependencies_mapping.items():
        module_path = Path(module)
        classpath_path = module_path.joinpath(classpath_file_subpath)
        print(str(classpath_path))
        merge_dependencies_with_classpath(classpath_path, module_dependencies)

'''modules_dependencies - {module_path : [dependency1, dependency2, ...]}
takes given dependencies and scans them on p2 repository to get exported packages
'''
def consider_exported_dependencies(modules_dependencies: Dict[str, List[str]], p2_repository: Path, scan_level=2):
    p2_repository_plugins = p2_repository.joinpath("pool/plugins")
    def consider_exported_dependencies_per_module(module: str, dependencies: List[str]):
        
    return dict(map(consider_exported_dependencies_per_module, modules_dependencies))    

mapped_dependencies = build_dependencies_paths_for_submodules(eclipse_project_path, submodules_relative_paths, Path(args.p2))
print("modules dependencies mapped to p2 repository")
pretty_print_header(mapped_dependencies, lengths=True)


# fill_classpaths_with_deps(mapped_dependencies)
