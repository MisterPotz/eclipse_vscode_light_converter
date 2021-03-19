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
parser.add_argument("-clean_cache", dest="clean_cache",
                    action="store_const", const=True, default=False)
parser.add_argument("-cache_path", dest="cache_folder", type=str,
                    help="Path to the cache folder to store parsed dependencies")
args = parser.parse_args()

to_code = args.to_code and not args.to_eclipse
cache_folder = args.cache_folder
print("eclipse project path {} \n submodules relative paths {} \n p2 repository path {} \n will convert to code {} and will clean cache {} in cache folder {}".format(
    args.eclipse_project_path,
    args.submodules_paths,
    args.p2,
    to_code,
    args.clean_cache,
    cache_folder
))
assert (to_code and args.p2 is not None) or not to_code, "Tried to convert to code format but no path to p2 repository was given"
assert (cache_folder is not None or not to_code), "Cache folder must not be null if convert to code"
# PREPARE THE INPUT
eclipse_project_path = args.eclipse_project_path
submodules_relative_paths = args.submodules_paths.strip().split()
clean_cache = args.clean_cache
submodules_relative_paths = list(
    map(lambda x: x.strip(), submodules_relative_paths))

print(submodules_relative_paths)

# MAIN CODE


def convert_eclipse_to_code(project_path1, modules: List[str], cache_folder: str, clean_cache=False):
    projects = list(map(lambda x: Project(project_path1, x), modules))
    project_bundles = list(map(lambda x: Bundle(
        args.p2, x.module_root, x, cache_folder), projects))
    configure_vs_code_settings(Path(project_path1))
    for i in project_bundles:
        i.update_dependencies()
        print(i)
        # cache dependencies and merge classpath files of each submodule
        i.merge_with_classpath(clean_cache=clean_cache)
        # need to add magic line if there is no such - makes some red highlight go away
        i.add_magic_line_to_settings()


def convert_code_to_eclipse(project_path: str, modules: List[str]):
    projects = list(map(lambda x: Project(project_path, x), modules))
    project_bundles = list(
        map(lambda x: Bundle(args.p2, x.module_root, x), projects))
    for i in project_bundles:
        i.clean_classpath()


if (to_code):
    convert_eclipse_to_code(
        eclipse_project_path, submodules_relative_paths, cache_folder, clean_cache)
else:
    convert_code_to_eclipse(eclipse_project_path, submodules_relative_paths)
