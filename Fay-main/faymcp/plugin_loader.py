import os
import sys
import json
import importlib
from types import ModuleType

class Tool:
    def __init__(self, name, description, input_schema, module, func):
        self.name = name
        self.description = description
        self.inputSchema = input_schema
        self.module = module
        self.func = func

def load_tools_from_folder(plugins_folder="faymcp/fay_plugins"):
    tools = []
    abs_path = os.path.abspath(plugins_folder)
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)  # so Python can import modules

    for item in os.listdir(plugins_folder):
        item_path = os.path.join(plugins_folder, item)
        if not os.path.isdir(item_path):
            continue

        # Look for a .json manifest file
        for file in os.listdir(item_path):
            if file.endswith(".json"):
                json_path = os.path.join(item_path, file)
                with open(json_path, "r", encoding="utf-8") as f:
                    try:
                        spec = json.load(f)
                    except Exception as e:
                        print(f"[PluginLoader] Failed to parse {file}: {e}")
                        continue

                module_path = spec.get("python_module")
                function_name = spec.get("python_function")
                tool_name = spec.get("name")
                description = spec.get("description", "")
                input_schema = spec.get("parameters", {})

                if not module_path or not function_name:
                    print(f"[PluginLoader] Skipping {file}: missing fields")
                    continue

                try:
                    module: ModuleType = importlib.import_module(module_path)
                    func = getattr(module, function_name)
                    tool = Tool(tool_name, description, input_schema, module, func)
                    tools.append(tool)
                    print(f"[PluginLoader] Loaded tool: {tool_name}")
                except Exception as e:
                    print(f"[PluginLoader] Failed to load {tool_name}: {e}")
    return tools
