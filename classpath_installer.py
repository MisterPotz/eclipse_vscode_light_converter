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
from pathlib import Path, PurePosixPath
import re
import argparse
from dependency import *

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
assert (to_code and args.p2 is not None) or not to_code, "Tried to convert to code format but no path to p2 repository was given"

# PREPARE THE INPUT
eclipse_project_path = args.eclipse_project_path
submodules_relative_paths = args.submodules_paths.strip().split()
submodules_relative_paths = list(
    map(lambda x: x.strip(), submodules_relative_paths))

print(submodules_relative_paths)

# MAIN CODE

def inflate_classpaths_with_parsed_dependencies(project_path: str, modules: List[str]):
    projects = list(map(lambda x : Project(project_path, x), modules))
    project_bundles = list(map(lambda x : Bundle(args.p2, x.module_root, x), projects))
    for i in project_bundles:
        i.update_dependencies()
        print(i)
        pretty_print(i.collect_exported_dependencies())
        i.merge_with_classpath()

def delete_autogens(project_path: str, modules: List[str]):
    projects = list(map(lambda x : Project(project_path, x), modules))
    project_bundles = list(map(lambda x : Bundle(args.p2, x.module_root, x), projects))
    for i in project_bundles:
        i.clean_classpath()

# inflate_classpaths_with_parsed_dependencies(eclipse_project_path, submodules_relative_paths)

if (to_code):
    inflate_classpaths_with_parsed_dependencies(eclipse_project_path, submodules_relative_paths)
else:
    delete_autogens(eclipse_project_path, submodules_relative_paths)