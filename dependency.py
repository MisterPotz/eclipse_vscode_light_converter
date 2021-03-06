
from pathlib import Path
from typing import List
import zipfile
import re

manifest_path = "META-INF/MANIFEST.MF"
dependency_declaration_keyword = "Require-Bundle"
dependency_declaration_word_end = ":"

class Dependency:
    def __init__(self, dependency_manifest_string):
        params = dependency_manifest_string.split(';')
        self.name = params[0]
        self.exported = dependency_manifest_string.find("reexport") > 0

    def __str__(self):
        return f"{self.name} : exported {self.exported}"

    def __repr__(self):
        return f"{self.name} : exported {self.exported}"


class Bundle:
    def __init__(self, p2_rep: Path, name: str):
        self.p2_rep = p2_rep
        self.name = name
        self.jars = []
        self.all_pattern = r"({})(\.source)?_[\.a-zA-Z0-9-]+\.jar".format(self.name)
        self.header_pattern = r"({})_[\.a-zA-Z0-9-]+\.jar".format(self.name)
        self.dependencies = []

    def plugins_path(self):
        return self.p2_rep.joinpath("pool/plugins")

    def jars_paths(self):
        plugins = self.plugins_path()
        return list(map(lambda x: plugins.joinpath(x), self.jars))

    def update_jars(self):
        plugins = self.plugins_path()
        bundles = plugins.glob("*.jar")
        string = self.all_pattern
        pattern = re.compile(string)
        bundles = list(bundles)
        jars = list(filter(lambda x: re.fullmatch(pattern, x.stem + x.suffix) is not None, bundles))
        jars = list(map(lambda x: str(x.stem + x.suffix), jars))
        self.jars = jars

    def get_manifest_file(self):
        pattern = re.compile(self.header_pattern)
        not_source = list(filter(lambda x : re.fullmatch(pattern, x), self.jars))
        if len(not_source) == 0:
            return None
        return self.plugins_path().joinpath(not_source[0])

    def get_manifest_file_lines(self):
        file = self.get_manifest_file()
        zip1 = zipfile.ZipFile(file)
        manifest_file = zipfile.Path(zip1).joinpath(manifest_path)
        lines = []
        with manifest_file.open('r') as file:
            lines = file.readlines()
        return list(map(lambda x : x.decode('utf8').rstrip("\n\r"), lines))

    def update_dependencies(self):
        manifest_lines = self.get_manifest_file_lines()
        dependencies = parse_manifest_file_lines(manifest_lines)
        self.dependencies = dependencies

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
                    new_lines.append(lines[last_index:index])
                    last_index = index + 1
        new_lines.append(lines[last_index:])
        return new_lines

def parse_manifest_file_lines(lines) -> List[Dependency]:
    require_block_declaration_pattern = re.compile(r"({})*:[\ ]*.*".format(dependency_declaration_keyword))
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
    lines = lines.strip()[lines.find(dependency_declaration_keyword) + len(dependency_declaration_keyword + dependency_declaration_word_end):]
    lines = split_by_commas(lines)
    # can be case when ',' was inside brackets
    dependencies = list(map(lambda x: Dependency(x), lines))
    return dependencies