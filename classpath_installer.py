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

# CONSTS
import argparse
from os import sep
from typing import Dict, List
import re
import sys
from pathlib import Path, PurePosixPath
from functools import reduce #python 3
import operator
classpath_file_subpath = ".classpath"
dependency_declaration_subpath = "META-INF/MANIFEST.MF"
dependency_declaration_keyword = "Require-Bundle"
dependency_declaration_word_end = ":"


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

def parse_dependencies_for_file(file: Path) -> List[str]:
    lines_to_parse = []
    with file.open("r") as open_file:
        # need to find a line with "Require-Bundle"
        in_require_block = False
        for line in open_file.readlines():
            if (line
                    .strip()
                    .startswith(dependency_declaration_keyword)):
                line = line[line.index(dependency_declaration_word_end)+1:]
                in_require_block = True
            if (in_require_block):
                line = line.strip()
                possible_first_end_1 = line.find(';')
                possible_first_end_2 = line.find(",")
                end = min(possible_first_end_1, possible_first_end_2)
                if (possible_first_end_1 < 0 and possible_first_end_2 < 0):
                    # could possibly mean end of block
                    end = len(line)
                    in_require_block = False
                elif (possible_first_end_1 < 0):
                    end = possible_first_end_2
                elif (possible_first_end_2 < 0):
                    end = possible_first_end_1
                    # if there is no second type of character that is definitely end of block
                    in_require_block = False
                lines_to_parse.append(line[:end])
                if (not in_require_block):
                    return lines_to_parse
    return lines_to_parse

def paths_for_submodules(project_root: Path, submodules: List[str]):
    return list(map(lambda x: Path(f"{eclipse_project_path}/{x}"), submodules_relative_paths))

def parse_dependencies_for_submodules(project_root: Path, submodules: List[str]) -> Dict[str, str]:
    paths = paths_for_submodules(project_root, submodules)
    module_dependencies: Dict[str, str] = {}

    for i in paths:
        dependency_file = i.joinpath(dependency_declaration_subpath)
        i_dependencies = (parse_dependencies_for_file(dependency_file))
        module_dependencies[str(i)] = i_dependencies

    for key, value in zip(module_dependencies, module_dependencies.values()):
        print(key)
        for string in value:
            print("\t" + string)
    return module_dependencies


def map_dependencies_to_p2_repository(module_dependencies: Dict[str, str], p2_repository: Path) -> Dict[str, str]:
    set_of_all_deps = reduce(operator.concat, module_dependencies.values())
    plugins_path = p2_repository.joinpath("pool/plugins")
    print(set_of_all_deps)
    all_files_iterator = plugins_path.glob(r"*.jar")
    dependency_paths : Dict[str, List[str]]= {}
    for i in all_files_iterator:
        print(str(i))
        for g in set_of_all_deps:
            if (str(i).find(g) >= 0):
                # a match, must save
                if (g not in dependency_paths):
                    dependency_paths[g] = []
                dependency_paths[g].append(str(i))
    for i, value in zip(dependency_paths, dependency_paths.values()):
        print()
        print(i, value, sep="\t")

def merge_dependencies_with_classpath(file: Path, dependencies: List[str]):
    with file.open('rb+') as opened_file:
        byt_arr = opened_file.read()
        insertion_index = byt_arr.find(b"</classpath>")
        if (insertion_index > 0):
            opened_file.seek(insertion_index - 1, 0)
            for dependency in dependencies:
                line = '<classpathentry exported="true" kind="lib" path="thirdparty/gson/lib/gson-2.6.2.jar"/>'
                opened_file.write("clas")
            
dependencies = parse_dependencies_for_submodules(eclipse_project_path, submodules_relative_paths)

# for i in paths_for_submodules(eclipse_project_path, submodules_relative_paths):
#     merge_dependencies_with_classpath(i.joinpath(classpath_file_subpath), dependencies[str(i)])

map_dependencies_to_p2_repository(dependencies, Path(args.p2))
