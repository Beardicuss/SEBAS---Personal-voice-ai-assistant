# -*- coding: utf-8 -*-
"""
Code Skill - Voice-to-code functionality with code generation, editing, and validation
"""

from skills.base_skill import BaseSkill
from typing import Dict, List, Any, Optional, Tuple
import os
import ast
import re
import json
import string
from pathlib import Path
import logging


class CodeSkill(BaseSkill):
    """
    Skill for voice-to-code functionality inspired by Talon Voice and Serenade AI.
    Supports code generation, editing, and validation across multiple languages.
    """

    def __init__(self, assistant_ref):
        super().__init__(assistant_ref)
        self.templates_dir = os.path.join(os.path.dirname(__file__), 'code_templates')
        self.generated_code_dir = os.path.join(os.path.expanduser('~'), 'sebas_generated_code')
        self.config_file = os.path.join(os.path.expanduser('~'), '.sebas_code_config.json')

        # Ensure directories exist
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.generated_code_dir, exist_ok=True)

        # Code generation settings - define BEFORE loading templates
        self.supported_languages = ['python', 'javascript', 'java', 'cpp', 'c', 'csharp']

        # Load configuration and templates
        self.config = self._load_config()
        self.templates = self._load_templates()
        self.dangerous_patterns = [
            r'import\s+os\s*\.\s*system',
            r'import\s+subprocess',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'open\s*\(\s*.*\s*[\'"]w[\'"]',
            r'\.delete\s*\(',
            r'\.remove\s*\(',
            r'os\.remove',
            r'os\.rmdir',
            r'shutil\.rmtree'
        ]

    def get_intents(self) -> List[str]:
        return [
            'create_function',
            'create_class',
            'generate_loop',
            'generate_conditional',
            'add_code_to_function',
            'insert_statement',
            'generate_variable',
            'create_snippet',
            'validate_code',
            'open_generated_code',
            'save_code_snippet',
            'list_code_snippets',
            'configure_code_settings'
        ]

    def can_handle(self, intent: str) -> bool:
        return intent in self.get_intents()

    def handle(self, intent: str, slots: Dict[str, Any]) -> bool:
        try:
            if intent == 'create_function':
                return self._handle_create_function(slots)
            elif intent == 'create_class':
                return self._handle_create_class(slots)
            elif intent == 'generate_loop':
                return self._handle_generate_loop(slots)
            elif intent == 'generate_conditional':
                return self._handle_generate_conditional(slots)
            elif intent == 'add_code_to_function':
                return self._handle_add_code_to_function(slots)
            elif intent == 'insert_statement':
                return self._handle_insert_statement(slots)
            elif intent == 'generate_variable':
                return self._handle_generate_variable(slots)
            elif intent == 'create_snippet':
                return self._handle_create_snippet(slots)
            elif intent == 'validate_code':
                return self._handle_validate_code(slots)
            elif intent == 'open_generated_code':
                return self._handle_open_generated_code(slots)
            elif intent == 'save_code_snippet':
                return self._handle_save_code_snippet(slots)
            elif intent == 'list_code_snippets':
                return self._handle_list_code_snippets()
            elif intent == 'configure_code_settings':
                return self._handle_configure_code_settings(slots)
            return False
        except Exception as e:
            self.logger.exception(f"Error handling code intent {intent}")
            self.assistant.speak("An error occurred while processing the code command")
            return False

    def _load_config(self) -> Dict[str, Any]:
        """Load code generation configuration"""
        try:
            if os.path.isfile(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.exception("Failed to load code config")

        # Default configuration
        return {
            'default_language': 'python',
            'indent_style': 'spaces',
            'indent_size': 4,
            'auto_save': True,
            'safety_checks': True,
            'max_snippet_size': 10000
        }

    def _save_config(self):
        """Save code generation configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.exception("Failed to save code config")

    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load code templates from templates directory"""
        templates = {}

        # Default language templates
        templates['python'] = {
            'function': 'def {name}({params}):\n    """{description}"""\n    {body}\n    return {return_value}',
            'class': 'class {name}:\n    """{description}"""\n    \n    def __init__(self{init_params}):\n        {init_body}\n    \n    {methods}',
            'for_loop': 'for {variable} in {iterable}:\n    {body}',
            'while_loop': 'while {condition}:\n    {body}',
            'if_statement': 'if {condition}:\n    {body}\nelif {elif_condition}:\n    {elif_body}\nelse:\n    {else_body}',
            'try_except': 'try:\n    {try_body}\nexcept {exception_type} as {exception_var}:\n    {except_body}',
            'variable': '{name} = {value}',
            'method': 'def {name}(self{params}):\n    """{description}"""\n    {body}\n    return {return_value}'
        }

        templates['javascript'] = {
            'function': 'function {name}({params}) {{\n    // {description}\n    {body}\n    return {return_value};\n}}',
            'class': 'class {name} {{\n    // {description}\n    \n    constructor({init_params}) {{\n        {init_body}\n    }}\n    \n    {methods}\n}}',
            'for_loop': 'for (let {variable} of {iterable}) {{\n    {body}\n}}',
            'while_loop': 'while ({condition}) {{\n    {body}\n}}',
            'if_statement': 'if ({condition}) {{\n    {body}\n}} else if ({elif_condition}) {{\n    {elif_body}\n}} else {{\n    {else_body}\n}}',
            'try_catch': 'try {{\n    {try_body}\n}} catch ({exception_var}) {{\n    {catch_body}\n}}',
            'variable': 'const {name} = {value};',
            'method': '{name}({params}) {{\n    // {description}\n    {body}\n    return {return_value};\n}}'
        }

        # Load custom templates from files
        try:
            for lang in self.supported_languages:
                template_file = os.path.join(self.templates_dir, f'{lang}_templates.json')
                if os.path.isfile(template_file):
                    with open(template_file, 'r', encoding='utf-8') as f:
                        lang_templates = json.load(f)
                        templates[lang].update(lang_templates)
        except Exception as e:
            self.logger.exception("Failed to load custom templates")

        return templates

    def _get_language_from_slots(self, slots: Dict[str, Any]) -> str:
        """Determine programming language from slots"""
        language = slots.get('language', '').lower().strip()
        if language in self.supported_languages:
            return language
        return self.config.get('default_language', 'python')

    def _validate_code_safety(self, code: str, language: str) -> Tuple[bool, str]:
        """Validate code for safety concerns"""
        if not self.config.get('safety_checks', True):
            return True, ""

        code_lower = code.lower()

        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code_lower):
                return False, f"Code contains potentially dangerous operation: {pattern}"

        # Language-specific safety checks
        if language == 'python':
            return self._validate_python_safety(code)

        return True, ""

    def _validate_python_safety(self, code: str) -> Tuple[bool, str]:
        """Python-specific safety validation"""
        try:
            # Parse AST to check for dangerous constructs
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ['eval', 'exec', 'open', 'system', 'popen', 'call', 'run']:
                            return False, f"Potentially unsafe function call: {func_name}"

                # Check for dangerous attribute access
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.attr, str):
                        if node.attr in ['system', 'popen', 'call', 'run', 'eval', 'exec']:
                            return False, f"Potentially unsafe attribute access: {node.attr}"

            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error in Python code: {str(e)}"
        except Exception as e:
            self.logger.exception("Error during Python AST validation")
            return False, f"Code validation error: {str(e)}"

    def _generate_function(self, language: str, name: str, description: str = "", params: str = "") -> str:
        """Generate function code"""
        template = self.templates.get(language, {}).get('function', '')
        if not template:
            return f"# Function template not available for {language}"

        # Parse parameters
        param_list = []
        if params:
            param_list = [p.strip() for p in params.split(',')]

        # Generate parameter string based on language
        if language == 'python':
            param_str = ', '.join(param_list)
        elif language == 'javascript':
            param_str = ', '.join(param_list)
        else:
            param_str = ', '.join(param_list)

        # Generate function body placeholder
        if language == 'python':
            body = '    # TODO: Implement function logic\n    pass'
            return_val = 'None'
        elif language == 'javascript':
            body = '    // TODO: Implement function logic\n    // return something;'
            return_val = 'null'
        else:
            body = '    // TODO: Implement function logic'
            return_val = ''

        return template.format(
            name=name,
            params=param_str,
            description=description or f"Function {name}",
            body=body,
            return_value=return_val
        )

    def _generate_class(self, language: str, name: str, description: str = "") -> str:
        """Generate class code"""
        template = self.templates.get(language, {}).get('class', '')
        if not template:
            return f"// Class template not available for {language}"

        if language == 'python':
            init_params = '(self)'
            init_body = '        # Initialize class attributes\n        pass'
            methods = '    # TODO: Add class methods'
        elif language == 'javascript':
            init_params = '()'
            init_body = '        // Initialize class properties\n        // this.property = value;'
            methods = '    // TODO: Add class methods'
        else:
            init_params = '()'
            init_body = '        // Initialize class properties'
            methods = '    // TODO: Add class methods'

        return template.format(
            name=name,
            description=description or f"Class {name}",
            init_params=init_params,
            init_body=init_body,
            methods=methods
        )

    def _generate_loop(self, language: str, loop_type: str, variable: str = "", iterable: str = "", condition: str = "") -> str:
        """Generate loop code"""
        if loop_type.lower() in ['for', 'foreach']:
            template = self.templates.get(language, {}).get('for_loop', '')
            if not template:
                return f"// For loop template not available for {language}"

            if not variable:
                variable = 'item' if language == 'python' else 'item'
            if not iterable:
                iterable = 'items' if language == 'python' else 'items'

            body = '    # TODO: Loop body\n    pass' if language == 'python' else '    // TODO: Loop body'

            return template.format(variable=variable, iterable=iterable, body=body)

        elif loop_type.lower() == 'while':
            template = self.templates.get(language, {}).get('while_loop', '')
            if not template:
                return f"// While loop template not available for {language}"

            if not condition:
                condition = 'True' if language == 'python' else 'true'

            body = '    # TODO: Loop body\n    pass' if language == 'python' else '    // TODO: Loop body'

            return template.format(condition=condition, body=body)

        return f"// Unsupported loop type: {loop_type}"

    def _handle_create_function(self, slots: Dict[str, Any]) -> bool:
        language = self._get_language_from_slots(slots)
        name = slots.get('name', '').strip()
        description = slots.get('description', '').strip()
        params = slots.get('params', '').strip()

        if not name:
            self.assistant.speak("Please specify a function name")
            return False

        code = self._generate_function(language, name, description, params)

        # Validate safety
        is_safe, safety_msg = self._validate_code_safety(code, language)
        if not is_safe:
            self.assistant.speak(f"Generated code failed safety check: {safety_msg}")
            return False

        # Speak the generated code
        self.assistant.speak(f"Generated {language} function {name}")

        # Optionally save to file
        if self.config.get('auto_save', True):
            filename = f"{name}.{self._get_file_extension(language)}"
            filepath = os.path.join(self.generated_code_dir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code)
                self.assistant.speak(f"Code saved to {filename}")
            except Exception as e:
                self.logger.exception(f"Failed to save generated function to {filepath}")

        return True

    def _handle_create_class(self, slots: Dict[str, Any]) -> bool:
        language = self._get_language_from_slots(slots)
        name = slots.get('name', '').strip()
        description = slots.get('description', '').strip()

        if not name:
            self.assistant.speak("Please specify a class name")
            return False

        code = self._generate_class(language, name, description)

        # Validate safety
        is_safe, safety_msg = self._validate_code_safety(code, language)
        if not is_safe:
            self.assistant.speak(f"Generated code failed safety check: {safety_msg}")
            return False

        self.assistant.speak(f"Generated {language} class {name}")

        if self.config.get('auto_save', True):
            filename = f"{name}.{self._get_file_extension(language)}"
            filepath = os.path.join(self.generated_code_dir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code)
                self.assistant.speak(f"Code saved to {filename}")
            except Exception as e:
                self.logger.exception(f"Failed to save generated class to {filepath}")

        return True

    def _handle_generate_loop(self, slots: Dict[str, Any]) -> bool:
        language = self._get_language_from_slots(slots)
        loop_type = slots.get('type', 'for').strip()
        variable = slots.get('variable', '').strip()
        iterable = slots.get('iterable', '').strip()
        task = slots.get('task', '').strip()

        code = self._generate_loop(language, loop_type, variable, iterable)

        # Validate safety
        is_safe, safety_msg = self._validate_code_safety(code, language)
        if not is_safe:
            self.assistant.speak(f"Generated code failed safety check: {safety_msg}")
            return False

        self.assistant.speak(f"Generated {language} {loop_type} loop")

        if self.config.get('auto_save', True):
            filename = f"loop_{loop_type}.{self._get_file_extension(language)}"
            filepath = os.path.join(self.generated_code_dir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code)
                self.assistant.speak(f"Code saved to {filename}")
            except Exception as e:
                self.logger.exception(f"Failed to save generated loop to {filepath}")

        return True

    def _handle_generate_conditional(self, slots: Dict[str, Any]) -> bool:
        language = self._get_language_from_slots(slots)
        condition = slots.get('condition', '').strip()

        template = self.templates.get(language, {}).get('if_statement', '')
        if not template:
            self.assistant.speak(f"If statement template not available for {language}")
            return False

        if not condition:
            condition = 'True' if language == 'python' else 'true'

        body = '    # TODO: If body\n    pass' if language == 'python' else '    // TODO: If body'
        elif_body = '    # TODO: Elif body\n    pass' if language == 'python' else '    // TODO: Elif body'
        else_body = '    # TODO: Else body\n    pass' if language == 'python' else '    // TODO: Else body'

        code = template.format(
            condition=condition,
            body=body,
            elif_condition='False' if language == 'python' else 'false',
            elif_body=elif_body,
            else_body=else_body
        )

        # Validate safety
        is_safe, safety_msg = self._validate_code_safety(code, language)
        if not is_safe:
            self.assistant.speak(f"Generated code failed safety check: {safety_msg}")
            return False

        self.assistant.speak(f"Generated {language} conditional statement")

        if self.config.get('auto_save', True):
            filename = f"conditional.{self._get_file_extension(language)}"
            filepath = os.path.join(self.generated_code_dir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code)
                self.assistant.speak(f"Code saved to {filename}")
            except Exception as e:
                self.logger.exception(f"Failed to save generated conditional to {filepath}")

        return True

    def _handle_add_code_to_function(self, slots: Dict[str, Any]) -> bool:
        function_name = slots.get('function_name', '').strip()
        code_to_add = slots.get('code', '').strip()
        language = self._get_language_from_slots(slots)

        if not function_name or not code_to_add:
            self.assistant.speak("Please specify function name and code to add")
            return False

        # This is a simplified implementation - in practice, you'd need AST parsing
        # to safely modify existing code
        self.assistant.speak(f"Adding code to function {function_name}")

        # For now, just generate a new function with the added code
        code = self._generate_function(language, function_name, f"Function {function_name}", "")
        # This would need more sophisticated code modification logic

        return True

    def _handle_insert_statement(self, slots: Dict[str, Any]) -> bool:
        statement = slots.get('statement', '').strip()
        position = slots.get('position', '').strip()
        target = slots.get('target', '').strip()

        if not statement:
            self.assistant.speak("Please specify the statement to insert")
            return False

        self.assistant.speak(f"Inserting statement {position} {target}")
        # This would require more sophisticated code editing capabilities

        return True

    def _handle_generate_variable(self, slots: Dict[str, Any]) -> bool:
        language = self._get_language_from_slots(slots)
        name = slots.get('name', '').strip()
        value = slots.get('value', '').strip()

        if not name:
            self.assistant.speak("Please specify a variable name")
            return False

        if not value:
            value = 'None' if language == 'python' else 'null'

        template = self.templates.get(language, {}).get('variable', '')
        if not template:
            self.assistant.speak(f"Variable template not available for {language}")
            return False

        code = template.format(name=name, value=value)

        # Validate safety
        is_safe, safety_msg = self._validate_code_safety(code, language)
        if not is_safe:
            self.assistant.speak(f"Generated code failed safety check: {safety_msg}")
            return False

        self.assistant.speak(f"Generated {language} variable {name}")

        return True

    def _handle_create_snippet(self, slots: Dict[str, Any]) -> bool:
        language = self._get_language_from_slots(slots)
        name = slots.get('name', '').strip()
        description = slots.get('description', '').strip()

        if not name:
            self.assistant.speak("Please specify a snippet name")
            return False

        # For now, create an empty snippet file
        filename = f"snippet_{name}.{self._get_file_extension(language)}"
        filepath = os.path.join(self.generated_code_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {description or f'Snippet: {name}'}\n\n# TODO: Add snippet code\n")
            self.assistant.speak(f"Created code snippet {name}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to create snippet {filepath}")
            self.assistant.speak("Failed to create code snippet")
            return False

    def _handle_validate_code(self, slots: Dict[str, Any]) -> bool:
        language = self._get_language_from_slots(slots)
        code_path = slots.get('path', '').strip()

        if not code_path or not os.path.exists(code_path):
            self.assistant.speak("Please specify a valid code file path")
            return False

        try:
            with open(code_path, 'r', encoding='utf-8') as f:
                code = f.read()

            is_safe, safety_msg = self._validate_code_safety(code, language)
            if not is_safe:
                self.assistant.speak(f"Code validation failed: {safety_msg}")
                return False

            self.assistant.speak(f"Code in {os.path.basename(code_path)} passed validation")
            return True

        except Exception as e:
            self.logger.exception(f"Failed to validate code in {code_path}")
            self.assistant.speak("Failed to validate code")
            return False

    def _handle_open_generated_code(self, slots: Dict[str, Any]) -> bool:
        filename = slots.get('filename', '').strip()

        if not filename:
            self.assistant.speak("Please specify a filename")
            return False

        filepath = os.path.join(self.generated_code_dir, filename)
        if not os.path.exists(filepath):
            self.assistant.speak("Generated code file not found")
            return False

        try:
            os.startfile(filepath)
            self.assistant.speak(f"Opening {filename}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to open generated code {filepath}")
            self.assistant.speak("Failed to open generated code")
            return False

    def _handle_save_code_snippet(self, slots: Dict[str, Any]) -> bool:
        name = slots.get('name', '').strip()
        code = slots.get('code', '').strip()
        language = self._get_language_from_slots(slots)

        if not name or not code:
            self.assistant.speak("Please specify snippet name and code")
            return False

        # Validate safety
        is_safe, safety_msg = self._validate_code_safety(code, language)
        if not is_safe:
            self.assistant.speak(f"Code failed safety check: {safety_msg}")
            return False

        filename = f"snippet_{name}.{self._get_file_extension(language)}"
        filepath = os.path.join(self.generated_code_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            self.assistant.speak(f"Saved code snippet {name}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to save code snippet {filepath}")
            self.assistant.speak("Failed to save code snippet")
            return False

    def _handle_list_code_snippets(self) -> bool:
        if not os.path.exists(self.generated_code_dir):
            self.assistant.speak("No generated code directory found")
            return True

        try:
            files = os.listdir(self.generated_code_dir)
            if not files:
                self.assistant.speak("No code snippets found")
                return True

            snippets = [f for f in files if f.endswith(('.py', '.js', '.java', '.cpp', '.c', '.cs'))]
            if not snippets:
                self.assistant.speak("No code snippets found")
                return True

            snippet_list = ", ".join(snippets[:10])  # Limit to 10
            self.assistant.speak(f"Available code snippets: {snippet_list}")
            return True

        except Exception as e:
            self.logger.exception("Failed to list code snippets")
            self.assistant.speak("Failed to list code snippets")
            return False

    def _handle_configure_code_settings(self, slots: Dict[str, Any]) -> bool:
        setting = slots.get('setting', '').strip()
        value = slots.get('value', '').strip()

        if not setting:
            self.assistant.speak("Please specify a setting to configure")
            return False

        # Handle different settings
        if setting == 'language':
            if value.lower() in self.supported_languages:
                self.config['default_language'] = value.lower()
                self._save_config()
                self.assistant.speak(f"Default language set to {value}")
            else:
                self.assistant.speak(f"Unsupported language. Supported: {', '.join(self.supported_languages)}")
                return False

        elif setting == 'auto_save':
            if value.lower() in ['true', 'false', 'on', 'off']:
                self.config['auto_save'] = value.lower() in ['true', 'on']
                self._save_config()
                self.assistant.speak(f"Auto save {'enabled' if self.config['auto_save'] else 'disabled'}")
            else:
                self.assistant.speak("Please specify true or false for auto save")
                return False

        elif setting == 'safety':
            if value.lower() in ['true', 'false', 'on', 'off']:
                self.config['safety_checks'] = value.lower() in ['true', 'on']
                self._save_config()
                self.assistant.speak(f"Safety checks {'enabled' if self.config['safety_checks'] else 'disabled'}")
            else:
                self.assistant.speak("Please specify true or false for safety checks")
                return False

        else:
            self.assistant.speak(f"Unknown setting: {setting}")
            return False

        return True

    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language"""
        extensions = {
            'python': 'py',
            'javascript': 'js',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'csharp': 'cs'
        }
        return extensions.get(language, 'txt')