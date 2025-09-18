#!/usr/bin/env python3
from backend.app.models import project_root
from importloader import ProjectImportAnalyzer, all_missing, analyzer, args, best_module, by_module, common, content, current_dir, current_imports, current_package, defined_symbols, exclude_dirs, file_key, full_path, imported_symbols, imports, insert_line, lines, main, missing, module_name, modules, name, new_imports, node, parser, parts, possible_modules, relative_path, response, score, scored_modules, stripped, symbols, symbols_str, total_missing, tree, used_symbols
"""
Comprehensive project-wide import scanner and fixer
Scans entire project, finds missing imports, and suggests/applies fixes
"""

import os
import ast
import sys
import re
import importlib.util
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional

class ProjectImportAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.python_files = []
        self.imports_map = defaultdict(set)  # {symbol: {possible_modules}}
        self.missing_imports = defaultdict(list)  # {file: [missing_symbols]}
        self.defined_symbols = defaultdict(set)  # {file: {defined_symbols}}
        self.used_symbols = defaultdict(set)  # {file: {used_symbols}}
        
    def scan_project(self):
        """Scan entire project for Python files and analyze imports"""
        print(f"🔍 Scanning project: {self.project_root}")
        
        # Find all Python files
        self.find_python_files()
        
        # Phase 1: Build symbol database
        print("📋 Phase 1: Building symbol database...")
        self.build_symbol_database()
        
        # Phase 2: Find missing imports
        print("🔍 Phase 2: Analyzing missing imports...")
        self.analyze_missing_imports()
        
        # Phase 3: Generate fixes
        print("🔧 Phase 3: Generating import fixes...")
        self.generate_fixes()
        
    def find_python_files(self):
        """Find all Python files in the project"""
        exclude_dirs = {
            '__pycache__', '.git', '.venv', 'venv', 'env', 
            'node_modules', '.pytest_cache', 'build', 'dist',
            '.tox', 'htmlcov'
        }
        
        for file_path in self.project_root.rglob("*.py"):
            # Skip excluded directories
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            self.python_files.append(file_path)
        
        print(f"Found {len(self.python_files)} Python files")
    
    def parse_file_safely(self, file_path: Path) -> Optional[ast.AST]:
        """Safely parse a Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ast.parse(content)
        except Exception as e:
            print(f"⚠️  Could not parse {file_path}: {e}")
            return None
    
    def build_symbol_database(self):
        """Build a database of all defined symbols in the project"""
        for file_path in self.python_files:
            tree = self.parse_file_safely(file_path)
            if not tree:
                continue
                
            relative_path = file_path.relative_to(self.project_root)
            module_name = self.path_to_module_name(relative_path)
            
            # Extract defined symbols
            defined_symbols = self.extract_defined_symbols(tree)
            self.defined_symbols[str(relative_path)] = defined_symbols
            
            # Map symbols to their modules
            for symbol in defined_symbols:
                self.imports_map[symbol].add(module_name)
            
            # Extract used symbols
            used_symbols = self.extract_used_symbols(tree)
            self.used_symbols[str(relative_path)] = used_symbols
    
    def path_to_module_name(self, relative_path: Path) -> str:
        """Convert file path to Python module name"""
        parts = list(relative_path.parts)
        if parts[-1] == '__init__.py':
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace('.py', '')
        
        return '.'.join(parts) if parts else ''
    
    def extract_defined_symbols(self, tree: ast.AST) -> Set[str]:
        """Extract all symbols defined in an AST"""
        symbols = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.add(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                symbols.add(node.name)
            elif isinstance(node, ast.ClassDef):
                symbols.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.add(target.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    symbols.add(name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        name = alias.asname or alias.name
                        symbols.add(name)
        
        return symbols
    
    def extract_used_symbols(self, tree: ast.AST) -> Set[str]:
        """Extract all symbols used in an AST"""
        symbols = set()
        imported_symbols = set()
        
        # First, collect imported symbols
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    imported_symbols.add(name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imported_symbols.add(name)
        
        # Then collect used symbols (excluding imported ones for now)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in imported_symbols:
                    symbols.add(node.id)
            elif isinstance(node, ast.Attribute):
                # For things like os.path.join, we want 'os'
                while isinstance(node.value, ast.Attribute):
                    node = node.value
                if isinstance(node.value, ast.Name):
                    if node.value.id not in imported_symbols:
                        symbols.add(node.value.id)
        
        return symbols
    
    def analyze_missing_imports(self):
        """Find missing imports in each file"""
        for file_path in self.python_files:
            relative_path = file_path.relative_to(self.project_root)
            file_key = str(relative_path)
            
            tree = self.parse_file_safely(file_path)
            if not tree:
                continue
            
            # Get current imports
            current_imports = self.get_current_imports(tree)
            
            # Get used symbols
            used_symbols = self.used_symbols[file_key]
            
            # Find missing imports
            missing = []
            for symbol in used_symbols:
                if symbol not in current_imports and symbol in self.imports_map:
                    # Find best module for this symbol
                    possible_modules = self.imports_map[symbol]
                    best_module = self.choose_best_module(symbol, possible_modules, file_path)
                    if best_module:
                        missing.append((symbol, best_module))
            
            if missing:
                self.missing_imports[file_key] = missing
    
    def get_current_imports(self, tree: ast.AST) -> Set[str]:
        """Get all currently imported symbols"""
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    imports.add(name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports.add(name)
        
        return imports
    
    def choose_best_module(self, symbol: str, possible_modules: Set[str], current_file: Path) -> Optional[str]:
        """Choose the best module to import a symbol from"""
        if not possible_modules:
            return None
        
        # Prefer modules in the same directory/package
        current_dir = current_file.parent
        
        scored_modules = []
        for module in possible_modules:
            score = 0
            
            # Prefer local modules
            if module.startswith('.'):
                score += 10
            
            # Prefer modules in same package
            current_package = str(current_dir.relative_to(self.project_root)).replace('/', '.').replace('\\', '.')
            if module.startswith(current_package):
                score += 5
            
            # Prefer shorter module names (less nested)
            score -= module.count('.')
            
            scored_modules.append((score, module))
        
        # Return the highest scored module
        scored_modules.sort(reverse=True)
        return scored_modules[0][1]
    
    def generate_fixes(self):
        """Generate and display import fixes"""
        if not self.missing_imports:
            print("✅ No missing imports found!")
            return
        
        print(f"\n🔧 Found missing imports in {len(self.missing_imports)} files:")
        print("=" * 60)
        
        total_missing = 0
        for file_path, missing_list in self.missing_imports.items():
            total_missing += len(missing_list)
            print(f"\n📁 {file_path}:")
            
            # Group by module
            by_module = defaultdict(list)
            for symbol, module in missing_list:
                by_module[module].append(symbol)
            
            for module, symbols in by_module.items():
                if len(symbols) == 1:
                    print(f"   from {module} import {symbols[0]}")
                else:
                    symbols_str = ", ".join(sorted(symbols))
                    print(f"   from {module} import {symbols_str}")
        
        print(f"\n📊 Summary: {total_missing} missing imports across {len(self.missing_imports)} files")
        self.show_common_missing_imports()
    
    def show_common_missing_imports(self):
        """Show the most commonly missing imports"""
        all_missing = []
        for missing_list in self.missing_imports.values():
            all_missing.extend([symbol for symbol, _ in missing_list])
        
        if not all_missing:
            return
        
        common = Counter(all_missing).most_common(10)
        print(f"\n🔝 Most commonly missing symbols:")
        for symbol, count in common:
            modules = ", ".join(sorted(self.imports_map[symbol]))
            print(f"   {symbol} ({count} files) -> Available in: {modules}")
    
    def apply_fixes(self, auto_fix: bool = False):
        """Apply the import fixes to files"""
        if not auto_fix:
            response = input("\n🤔 Do you want to apply these fixes? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Fixes not applied.")
                return
        
        print("\n🔧 Applying fixes...")
        
        for file_path, missing_list in self.missing_imports.items():
            full_path = self.project_root / file_path
            self.add_imports_to_file(full_path, missing_list)
        
        print("✅ Fixes applied!")
    
    def add_imports_to_file(self, file_path: Path, missing_imports: List[Tuple[str, str]]):
        """Add missing imports to a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Find where to insert imports (after existing imports)
            insert_line = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ')) or stripped.startswith('#'):
                    insert_line = i + 1
                elif stripped and not stripped.startswith(('"""', "'''")):
                    break
            
            # Group imports by module
            by_module = defaultdict(list)
            for symbol, module in missing_imports:
                by_module[module].append(symbol)
            
            # Generate import lines
            new_imports = []
            for module, symbols in sorted(by_module.items()):
                if len(symbols) == 1:
                    new_imports.append(f"from {module} import {symbols[0]}")
                else:
                    symbols_str = ", ".join(sorted(symbols))
                    new_imports.append(f"from {module} import {symbols_str}")
            
            # Insert the imports
            lines[insert_line:insert_line] = new_imports
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print(f"   ✅ Fixed {file_path}")
            
        except Exception as e:
            print(f"   ❌ Failed to fix {file_path}: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan and fix missing imports in Python project")
    parser.add_argument("project_path", nargs="?", default=".", 
                       help="Path to project root (default: current directory)")
    parser.add_argument("--fix", action="store_true", 
                       help="Automatically apply fixes without prompting")
    parser.add_argument("--apply", action="store_true", 
                       help="Apply fixes after analysis")
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = ProjectImportAnalyzer(args.project_path)
    
    # Scan project
    analyzer.scan_project()
    
    # Apply fixes if requested
    if args.apply:
        analyzer.apply_fixes(auto_fix=args.fix)

if __name__ == "__main__":
    main()