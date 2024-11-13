import re
from pathlib import Path
from typing import List, Set, Dict
import networkx as nx
from dataclasses import dataclass

@dataclass
class ModuleInfo:
    """Information about a Python module"""
    path: Path
    content: str
    imports: Set[str]
    classes: Set[str]
    functions: Set[str]

class ChimeraCat:
    """Utility to concatenate modular code into Colab-friendly single files"""
    
    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.modules: Dict[Path, ModuleInfo] = {}
        self.dep_graph = nx.DiGraph()
        
    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """Analyze a Python file for imports and definitions"""
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find imports
        import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+([^#\n]+)'
        imports = set()
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            if match.group(1):  # from X import Y
                imports.add(match.group(1))
            else:  # import X
                imports.add(match.group(2).split(',')[0].strip())
                
        # Find class definitions
        class_pattern = r'class\s+(\w+)'
        classes = set(re.findall(class_pattern, content))
        
        # Find function definitions
        func_pattern = r'def\s+(\w+)'
        functions = set(re.findall(func_pattern, content))
        
        return ModuleInfo(
            path=file_path,
            content=content,
            imports=imports,
            classes=classes,
            functions=functions
        )
    
    def build_dependency_graph(self):
        """Build a dependency graph of all Python files"""
        # Find all Python files
        for file_path in self.src_dir.rglob("*.py"):
            if file_path.name != "__init__.py":
                module_info = self.analyze_file(file_path)
                self.modules[file_path] = module_info
                self.dep_graph.add_node(file_path)
        
        # Add edges for dependencies
        for file_path, module in self.modules.items():
            pkg_path = file_path.relative_to(self.src_dir).parent
            for imp in module.imports:
                # Convert import to potential file paths
                imp_parts = imp.split('.')
                for other_path in self.modules:
                    other_pkg = other_path.relative_to(self.src_dir).parent
                    if str(other_pkg) == '.'.join(imp_parts[:-1]):
                        self.dep_graph.add_edge(file_path, other_path)
    
    def generate_colab_file(self, output_file: str = "colab_combined.py") -> str:
        """Generate a single file combining all modules in dependency order"""
        self.build_dependency_graph()
        
        # Sort files by dependencies
        try:
            sorted_files = list(nx.topological_sort(self.dep_graph))
        except nx.NetworkXUnfeasible:
            print("Warning: Circular dependencies detected. Using simple ordering.")
            sorted_files = list(self.modules.keys())
        
        # External imports section
        external_imports = set()
        for module in self.modules.values():
            external_imports.update(imp for imp in module.imports 
                                 if not any(str(imp).startswith(str(p.relative_to(self.src_dir).parent)) 
                                          for p in self.modules))
        
        # Generate combined file
        output = [
            "# Generated by ChimeraCat",
            "# External imports",
            *sorted(f"import {imp}" for imp in external_imports if not imp.startswith('.')),
            "\n# Combined module code\n"
        ]
        
        added_content = set()
        for file_path in sorted_files:
            module = self.modules[file_path]
            
            # Add module header
            rel_path = file_path.relative_to(self.src_dir)
            output.append(f"\n# From {rel_path}")
            
            # Clean up imports and add content
            lines = []
            for line in module.content.split('\n'):
                # Skip internal imports and empty lines at start
                if not (line.startswith('from .') or line.startswith('import .') or 
                       (not lines and not line.strip())):
                    if not any(pattern in line for pattern in added_content):
                        lines.append(line)
            
            # Add non-duplicate content
            content = '\n'.join(lines)
            output.append(content)
            
            # Track added definitions to avoid duplicates
            added_content.update(module.classes)
            added_content.update(module.functions)
        
        # Write output
        with open(output_file, 'w') as f:
            f.write('\n'.join(output))
            
        return output_file
    
    def generate_colab_notebook(self, output_file: str = "colab_combined.ipynb"):
        """Generate a Jupyter notebook with the combined code"""
        py_file = self.generate_colab_file("temp_combined.py")
        
        with open(py_file, 'r') as f:
            code = f.read()
        
        # Create notebook structure
        notebook = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["# Generated Colab Notebook\n", 
                             "This notebook was automatically generated by ChimeraCat."]
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "source": code.split('\n'),
                    "execution_count": None,
                    "outputs": []
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## Usage Example"]
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "source": [
                        "# Example usage",
                        "with VocalSeparator(output_dir='test_output') as separator:",
                        "    result = separator.separate_and_analyze(",
                        "        vocal_paths=('track-09.wav', 'track-10.wav'),",
                        "        accompaniment_paths=('track-07.wav', 'track-08.wav'),",
                        "        start_time=90.0,",
                        "        duration=30.0",
                        "    )"
                    ],
                    "execution_count": None,
                    "outputs": []
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }
        
        import json
        with open(output_file, 'w') as f:
            json.dump(notebook, f, indent=2)
        
        Path("temp_combined.py").unlink()  # Clean up temporary file
        return output_file

def main():
    concat = ChimeraCat("src")
    notebook_file = concat.generate_colab_notebook()
    print(f"Generated notebook: {notebook_file}")
    py_file = concat.generate_colab_file()
    print(f"Generated Python file: {py_file}")

if __name__ == "__main__":
    main()
