#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import sys
import json
import time
import threading
import logging
from datetime import datetime
from flask_cors import CORS
from faymcp.mcp_client import McpClient
from utils import util

# from faymcp.plugin_loader import load_tools_from_folder


# 创建Flask应用
app = Flask(__name__)

# 添加CORS支持，允许所有来源的跨域请求
CORS(app, resources={r"/*": {"origins": "*"}})


# MCP服务器数据文件路径
MCP_DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'mcp_servers.json')

# 确保data目录存在
os.makedirs(os.path.dirname(MCP_DATA_FILE), exist_ok=True)

# 存储MCP客户端对象的字典，键为服务器ID
mcp_clients = {}

# 存储MCP服务器工具列表的字典，键为服务器ID
mcp_tools = {}

# 连接检查定时器
connection_check_timer = None

# 连接检查间隔（秒）
CONNECTION_CHECK_INTERVAL = 60

# 默认MCP服务器数据
default_mcp_servers = [
]

# 加载MCP服务器数据
def load_mcp_servers():
    try:
        if os.path.exists(MCP_DATA_FILE):
            with open(MCP_DATA_FILE, 'r', encoding='utf-8') as f:
                servers = json.load(f)
                # 确保所有服务器状态为离线
                for server in servers:
                    server['status'] = 'offline'
                    server['latency'] = '0ms'
                return servers
        else:
            # 如果文件不存在，使用默认数据并保存
            save_mcp_servers(default_mcp_servers)
            return default_mcp_servers
    except Exception as e:
        util.log(1, f"加载MCP服务器数据失败: {e}")
        return default_mcp_servers

# 保存MCP服务器数据
def save_mcp_servers(servers):
    try:
        # 创建要保存的服务器数据副本
        servers_to_save = []
        for server in servers:
            # 创建服务器数据的副本，不包含运行状态
            server_copy = {
                "id": server['id'],
                "name": server['name'],
                "ip": server['ip'],
                "connection_time": server.get('connection_time', ''),
                "key": server.get('key', '')  # 保存Key字段
            }
            servers_to_save.append(server_copy)
            
        with open(MCP_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(servers_to_save, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        util.log(1, f"保存MCP服务器数据失败: {e}")
        return False

# 初始化MCP服务器数据
mcp_servers = load_mcp_servers()

# 连接真实MCP服务器
def connect_to_real_mcp(server):
    """
    连接到真实的MCP服务器
    :param server: 服务器信息字典
    :return: (是否连接成功, 更新后的服务器信息, 可用工具列表)
    """
    global mcp_clients
    try:
        # 获取服务器IP、ID和Key
        ip = server['ip']
        server_id = server['id']
        api_key = server.get('key', '')  # 获取Key，如果不存在则为空字符串
        
        # 构建MCP服务器端点URL
        endpoint = ip
        # 创建MCP客户端，传入API密钥
        client = McpClient(endpoint, api_key)
        
        # 记录开始时间
        start_time = time.time()
        
        # 尝试连接并获取可用工具列表
        success, result = client.connect()
        
        # 计算延迟时间
        latency = int((time.time() - start_time) * 1000)
        
        if success:
            # 连接成功，更新服务器状态
            server['status'] = 'online'
            server['latency'] = f"{latency}ms"
            server['connection_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 保存客户端对象
            mcp_clients[server_id] = client
            
            return True, server, result
        else:
            # 连接失败，更新服务器状态
            server['status'] = 'offline'
            server['latency'] = '0ms'
            server['connection_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 如果连接失败，删除可能存在的客户端对象
            if server_id in mcp_clients:
                del mcp_clients[server_id]
                
            return False, server, []
    except Exception as e:
        util.log(1, f"连接MCP服务器失败: {e}")
        server['status'] = 'offline'
        server['latency'] = '0ms'
        
        # 如果连接失败，删除可能存在的客户端对象
        if server['id'] in mcp_clients:
            del mcp_clients[server['id']]
            
        return False, server, []

# 获取MCP客户端
def get_mcp_client(server_id):
    """
    获取指定服务器ID的MCP客户端对象
    :param server_id: 服务器ID
    :return: McpClient对象或None
    """
    return mcp_clients.get(server_id)

# 调用MCP服务器工具
def call_mcp_tool(server_id, method, params=None):
    """
    调用MCP服务器工具
    :param server_id: 服务器ID
    :param method: 方法名
    :param params: 参数字典
    :return: (是否成功, 结果或错误信息)
    """
    try:
        # 获取客户端对象
        client = get_mcp_client(server_id)
        if not client:
            return False, "未找到服务器连接"
            
        # 调用工具
        return client.call_tool(method, params)
    except Exception as e:
        util.log(1, f"调用MCP工具失败: {e}")
        return False, f"调用MCP工具失败: {str(e)}"

# 主页路由 - 直接重定向到Page3页面
@app.route('/')
def index():
    return redirect(url_for('page3'))

# MCP页面路由 - Page3.html
@app.route('/Page3')
def page3():
    # 传递MCP服务器数据到模板
    return render_template('Page3.html', mcp_servers=mcp_servers)

# 设置页面路由 - 为了处理模板中的链接，但实际重定向到Page3
@app.route('/setting')
def setting():
    return redirect(url_for('page3'))

# API路由 - 获取所有MCP服务器
@app.route('/api/mcp/servers', methods=['GET'])
def get_mcp_servers():
    return jsonify(mcp_servers)

# API路由 - 添加新MCP服务器
@app.route('/api/mcp/servers', methods=['POST'])
def add_mcp_server():
    data = request.json
    
    # 验证必要字段
    required_fields = ['name', 'ip']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"缺少必要字段: {field}"}), 400
    
    # 生成新ID (当前最大ID + 1)
    new_id = 1
    if mcp_servers:
        new_id = max(server['id'] for server in mcp_servers) + 1
    
    # 创建新服务器对象
    new_server = {
        "id": new_id,
        "name": data['name'],
        "status": "offline",
        "ip": data['ip'],
        "latency": "0ms",
        "connection_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "key": data.get('key', '')  # 添加Key字段，如果不存在则为空字符串
    }
    
    # 如果请求中包含 auto_connect 字段并且为 True，则尝试连接
    auto_connect = data.get('auto_connect', False)
    tools_list = []
    
    if auto_connect:
        try:
            # 尝试连接真实MCP服务器
            success, new_server, tools = connect_to_real_mcp(new_server)
            
            # 如果连接失败，仍然添加服务器，但状态为离线
            if not success:
                new_server['status'] = 'offline'
            else:
                # 处理工具列表，确保它是可序列化的
                if tools:
                    try:
                        # 尝试将工具对象转换为字典列表
                        for tool in tools:
                            if hasattr(tool, 'name'):
                                # 如果是对象，转换为字典
                                tool_dict = {
                                    'name': str(getattr(tool, 'name', '未知')),
                                    'description': str(getattr(tool, 'description', '')),
                                }
                                
                                # 处理 inputSchema
                                input_schema = getattr(tool, 'inputSchema', {})
                                if input_schema and isinstance(input_schema, dict):
                                    tool_dict['inputSchema'] = input_schema
                                else:
                                    tool_dict['inputSchema'] = {}
                                    
                                tools_list.append(tool_dict)
                            else:
                                # 如果是字典
                                if isinstance(tool, dict) and 'name' in tool:
                                    tools_list.append({
                                        'name': str(tool.get('name', '未知')),
                                        'description': str(tool.get('description', '')),
                                        'inputSchema': tool.get('inputSchema', {})
                                    })
                                else:
                                    # 其他情况，尝试转换为字符串
                                    tools_list.append({'name': str(tool), 'description': ''})
                    except Exception as e:
                        util.log(1, f"工具列表序列化失败: {e}")
                        # 如果转换失败，只返回工具名称
                        tools_list = [{'name': str(tool)} for tool in tools]
                
        except Exception as e:
            util.log(1, f"自动连接失败: {e}")
            new_server['status'] = 'offline'
    
    # 添加到服务器列表
    mcp_servers.append(new_server)
    save_mcp_servers(mcp_servers)
    
    # 返回新服务器信息
    return jsonify({
        "message": f"服务器 {new_server['name']} 已添加",
        "server": new_server,
        "tools": tools_list
    }), 201

# API路由 - 更新MCP服务器状态
@app.route('/api/mcp/servers/<int:server_id>/status', methods=['PUT'])
def update_server_status(server_id):
    data = request.json
    for server in mcp_servers:
        if server['id'] == server_id:
            server['status'] = data.get('status', server['status'])
            save_mcp_servers(mcp_servers)
            return jsonify(server)
    return jsonify({"error": "服务器未找到"}), 404

# API路由 - 重启MCP服务器
@app.route('/api/mcp/servers/<int:server_id>/restart', methods=['POST'])
def restart_server(server_id):
    for server in mcp_servers:
        if server['id'] == server_id:
            # 这里可以添加实际的重启逻辑
            server['status'] = 'online'
            server['connection_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_mcp_servers(mcp_servers)
            return jsonify({"message": f"服务器 {server['name']} 已重启", "server": server})
    return jsonify({"error": "服务器未找到"}), 404

# API路由 - 断开MCP服务器连接
@app.route('/api/mcp/servers/<int:server_id>/disconnect', methods=['POST'])
def disconnect_server(server_id):
    global mcp_servers, mcp_clients, mcp_tools
    for server in mcp_servers:
        if server['id'] == server_id:
            # 这里可以添加实际的断开连接逻辑
            server['status'] = 'offline'
            
            # 删除客户端对象
            if server_id in mcp_clients:
                del mcp_clients[server_id]
                
            # 清除缓存的工具列表
            if server_id in mcp_tools:
                del mcp_tools[server_id]
                
            save_mcp_servers(mcp_servers)
            return jsonify({"message": f"服务器 {server['name']} 已断开连接", "server": server})
    return jsonify({"error": "服务器未找到"}), 404

# API路由 - 连接MCP服务器
@app.route('/api/mcp/servers/<int:server_id>/connect', methods=['POST'])
def connect_server(server_id):
    global mcp_servers, mcp_tools
    for i, server in enumerate(mcp_servers):
        if server['id'] == server_id:
            try:
                # 尝试连接真实MCP服务器
                util.log(1, f"正在连接MCP服务器: {server['name']} ({server['ip']})")
                success, updated_server, tools = connect_to_real_mcp(server)
                
                # 更新服务器信息
                mcp_servers[i] = updated_server
                save_mcp_servers(mcp_servers)
                
                if success:
                    util.log(1, f"MCP服务器连接成功: {updated_server['name']}，获取到 {len(tools) if tools else 0} 个工具")
                    # 处理工具列表，确保它是可序列化的
                    tools_list = []
                    if tools:
                        try:
                            # 尝试将工具对象转换为字典列表
                            for tool in tools:
                                if hasattr(tool, 'name'):
                                    # 如果是对象，转换为字典
                                    tool_dict = {
                                        'name': str(getattr(tool, 'name', '未知')),
                                        'description': str(getattr(tool, 'description', '')),
                                    }
                                    
                                    # 处理 inputSchema
                                    input_schema = getattr(tool, 'inputSchema', {})
                                    if input_schema and isinstance(input_schema, dict):
                                        tool_dict['inputSchema'] = input_schema
                                    else:
                                        tool_dict['inputSchema'] = {}
                                        
                                    tools_list.append(tool_dict)
                                else:
                                    # 如果是字典
                                    if isinstance(tool, dict) and 'name' in tool:
                                        tools_list.append({
                                            'name': str(tool.get('name', '未知')),
                                            'description': str(tool.get('description', '')),
                                            'inputSchema': tool.get('inputSchema', {})
                                        })
                                    else:
                                        # 其他情况，尝试转换为字符串
                                        tools_list.append({'name': str(tool), 'description': ''})
                        except Exception as e:
                            util.log(1, f"工具列表序列化失败: {e}")
                            # 如果转换失败，只返回工具名称
                            tools_list = [{'name': str(tool)} for tool in tools]
                    
                    # 保存工具列表到全局字典中
                    mcp_tools[server_id] = tools_list
                    
                    return jsonify({
                        "message": f"服务器 {updated_server['name']} 已连接", 
                        "server": updated_server,
                        "tools": tools_list,
                        "success": True
                    })
                else:
                    util.log(1, f"MCP服务器连接失败: {updated_server['name']}")
                    return jsonify({
                        "message": f"服务器 {updated_server['name']} 连接失败", 
                        "server": updated_server,
                        "success": False
                    }), 500
            except Exception as e:
                return jsonify({
                    "message": f"服务器 {server['name']} 连接失败: {str(e)}", 
                    "server": server,
                    "success": False
                }), 500
    return jsonify({"error": "服务器未找到"}), 404

# API路由 - 删除MCP服务器
@app.route('/api/mcp/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    global mcp_servers
    for i, server in enumerate(mcp_servers):
        if server['id'] == server_id:
            # 如果服务器处于连接状态，先断开连接
            if server['status'] == 'online':
                # 删除客户端对象
                if server_id in mcp_clients:
                    del mcp_clients[server_id]
                
                # 清除缓存的工具列表
                if server_id in mcp_tools:
                    del mcp_tools[server_id]
                
                # 更新服务器状态
                server['status'] = 'offline'
            
            # 删除服务器
            deleted_server = mcp_servers.pop(i)
            save_mcp_servers(mcp_servers)
            return jsonify({"message": f"服务器 {deleted_server['name']} 已删除", "server": deleted_server})
    return jsonify({"error": "服务器未找到"}), 404

# API路由 - 调用MCP工具
@app.route('/api/mcp/servers/<int:server_id>/call', methods=['POST'])
def call_server_tool(server_id):
    data = request.json
    method = data.get('method')
    params = data.get('params', {})
    
    if not method:
        return jsonify({"error": "缺少方法名"}), 400
        
    success, result = call_mcp_tool(server_id, method, params)
    
    if success:
        # 处理结果，确保它是可序列化的
        try:
            # 尝试将结果转换为可序列化的格式
            if hasattr(result, '__dict__'):
                # 如果是对象，转换为字典
                result_dict = dict(vars(result))
                return jsonify({
                    "success": True,
                    "result": result_dict
                })
            else:
                # 如果已经是字典或其他可序列化对象
                return jsonify({
                    "success": True,
                    "result": result
                })
        except Exception as e:
            # 如果转换失败，返回字符串形式
            return jsonify({
                "success": True,
                "result": str(result)
            })
    else:
        return jsonify({
            "success": False,
            "error": result
        }), 500

# API路由 - 获取服务器工具列表
@app.route('/api/mcp/servers/<int:server_id>/tools', methods=['GET'])
def get_server_tools(server_id):
    global mcp_tools
    for server in mcp_servers:
        if server['id'] == server_id:
            # 检查服务器是否在线
            if server['status'] != 'online':
                return jsonify({
                    "success": False,
                    "message": "服务器离线",
                    "tools": []
                })
            
            # 检查是否已有缓存的工具列表
            if server_id in mcp_tools and mcp_tools[server_id]:
                # 使用缓存的工具列表，添加到结果中
                return jsonify({
                    "success": True,
                    "message": "获取工具列表成功（缓存）",
                    "tools": mcp_tools[server_id]
                })
                
            # 获取客户端对象
            client = get_mcp_client(server_id)
            if not client:
                return jsonify({
                    "success": False,
                    "message": "未找到服务器连接",
                    "tools": []
                })
                
            try:
                # 获取工具列表
                tools = client.list_tools()
                
                # 处理工具列表，确保它是可序列化的
                tools_list = []
                if tools:
                    try:
                        # 尝试将工具对象转换为字典列表
                        for tool in tools:
                            if hasattr(tool, 'name'):
                                # 如果是对象，转换为字典
                                tool_dict = {
                                    'name': str(getattr(tool, 'name', '未知')),
                                    'description': str(getattr(tool, 'description', '')),
                                }
                                
                                # 处理 inputSchema
                                input_schema = getattr(tool, 'inputSchema', {})
                                if input_schema and isinstance(input_schema, dict):
                                    tool_dict['inputSchema'] = input_schema
                                else:
                                    tool_dict['inputSchema'] = {}
                                    
                                tools_list.append(tool_dict)
                            else:
                                # 如果是字典
                                if isinstance(tool, dict) and 'name' in tool:
                                    tools_list.append({
                                        'name': str(tool.get('name', '未知')),
                                        'description': str(tool.get('description', '')),
                                        'inputSchema': tool.get('inputSchema', {})
                                    })
                                else:
                                    # 其他情况，尝试转换为字符串
                                    tools_list.append({'name': str(tool), 'description': ''})
                    except Exception as e:
                        util.log(1, f"工具列表序列化失败: {e}")
                        # 如果转换失败，只返回工具名称
                        tools_list = [{'name': str(tool)} for tool in tools]
                
                # 保存工具列表到全局字典中
                mcp_tools[server_id] = tools_list
                
                return jsonify({
                    "success": True,
                    "message": "获取工具列表成功",
                    "tools": tools_list
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "message": f"获取工具列表失败: {str(e)}",
                    "tools": []
                })
                
    return jsonify({
        "success": False,
        "message": "服务器未找到",
        "tools": []
    }), 404

# API路由 - 获取所有在线服务器的工具列表
@app.route('/api/mcp/servers/online/tools', methods=['GET'])
def get_all_online_server_tools():
    global mcp_servers, mcp_tools
    
    all_tools = []
    
    for server in mcp_servers:
        # 只处理在线服务器
        if server['status'] == 'online':
            server_id = server['id']
            
            # 检查是否有缓存的工具列表
            if server_id in mcp_tools and mcp_tools[server_id]:
                # 使用缓存的工具列表，添加到结果中
                all_tools.extend(mcp_tools[server_id])
            else:
                # 获取客户端对象
                client = get_mcp_client(server_id)
                if client:
                    try:
                        # 获取工具列表
                        tools = client.list_tools()
                        
                        # 处理工具列表，确保它是可序列化的
                        tools_list = []
                        if tools:
                            try:
                                # 尝试将工具对象转换为字典列表
                                for tool in tools:
                                    if hasattr(tool, 'name'):
                                        # 如果是对象，转换为字典
                                        tool_dict = {
                                            'name': str(getattr(tool, 'name', '未知')),
                                            'description': str(getattr(tool, 'description', '')),
                                        }
                                        
                                        # 处理 inputSchema
                                        input_schema = getattr(tool, 'inputSchema', {})
                                        if input_schema and isinstance(input_schema, dict):
                                            tool_dict['inputSchema'] = input_schema
                                        else:
                                            tool_dict['inputSchema'] = {}
                                            
                                        tools_list.append(tool_dict)
                                    else:
                                        # 如果是字典
                                        if isinstance(tool, dict) and 'name' in tool:
                                            tools_list.append({
                                                'name': str(tool.get('name', '未知')),
                                                'description': str(tool.get('description', '')),
                                                'inputSchema': tool.get('inputSchema', {})
                                            })
                                        else:
                                            # 其他情况，尝试转换为字符串
                                            tools_list.append({'name': str(tool), 'description': ''})
                            except Exception as e:
                                util.log(1, f"工具列表序列化失败: {e}")
                                # 如果转换失败，只返回工具名称
                                tools_list = [{'name': str(tool)} for tool in tools]
                        
                        # 保存工具列表到全局字典中
                        mcp_tools[server_id] = tools_list
                        
                        # 添加到结果中
                        all_tools.extend(tools_list)
                    except Exception as e:
                        util.log(1, f"获取服务器 {server['name']} 工具列表失败: {e}")
    
    # 去除重复的工具（基于工具名称）
    unique_tools = []
    tool_names = set()
    for tool in all_tools:
        if tool['name'] not in tool_names:
            tool_names.add(tool['name'])
            unique_tools.append(tool)
    
    return jsonify({
        "success": True,
        "message": "获取所有在线服务器工具列表成功",
        "tools": unique_tools
    })

# API路由 - 直接调用MCP工具（无需指定服务器ID）
@app.route('/api/mcp/tools/<string:tool_name>', methods=['POST'])
def call_mcp_tool_direct(tool_name):
    """
    直接调用MCP工具，自动选择在线服务器
    :param tool_name: 工具名称
    :return: 工具调用结果
    """
    global mcp_servers
    
    # 获取请求参数
    params = request.json or {}
    
    # 查找所有在线服务器
    online_servers = [server for server in mcp_servers if server['status'] == 'online']
    
    if not online_servers:
        return jsonify({
            "success": False,
            "error": "没有在线的MCP服务器"
        }), 404
    
    # 遍历在线服务器，尝试调用工具
    for server in online_servers:
        server_id = server['id']
        
        # 检查服务器是否有该工具
        client = get_mcp_client(server_id)
        if not client:
            continue
            
        try:
            # 获取工具列表
            tools = client.list_tools()
            tool_names = [str(getattr(tool, 'name', tool)) for tool in tools]
            
            # 检查工具是否存在
            if tool_name in tool_names:
                # 调用工具
                success, result = call_mcp_tool(server_id, tool_name, params)
                
                if success:
                    # 处理结果，确保它是可序列化的
                    try:
                        # 尝试将结果转换为可序列化的格式
                        if hasattr(result, '__dict__'):
                            # 如果是对象，转换为字典
                            result_dict = dict(vars(result))
                            return jsonify({
                                "success": True,
                                "result": result_dict,
                                "server": server['name']
                            })
                        else:
                            # 如果已经是字典或其他可序列化对象
                            return jsonify({
                                "success": True,
                                "result": result,
                                "server": server['name']
                            })
                    except Exception as e:
                        # 如果转换失败，返回字符串形式
                        return jsonify({
                            "success": True,
                            "result": str(result),
                            "server": server['name']
                        })
                else:
                    # 如果当前服务器调用失败，尝试下一个服务器
                    util.log(1, f"服务器 {server['name']} 调用工具 {tool_name} 失败: {result}")
                    continue
        except Exception as e:
            util.log(1, f"服务器 {server['name']} 获取工具列表失败: {e}")
            continue
    
    # 所有服务器都尝试过了，但都失败了
    return jsonify({
        "success": False,
        "error": f"没有找到支持 {tool_name} 工具的在线服务器，或者所有服务器调用都失败"
    }), 404

# 检查所有MCP客户端连接状态并自动重连
def check_mcp_connections():
    """
    定时检查所有MCP客户端连接状态，如果发现断线则自动重连
    """
    global mcp_servers, mcp_clients, connection_check_timer
    
    # util.log(1, "正在检查MCP客户端连接状态...")
    reconnected_servers = []
    
    for server in mcp_servers:
        server_id = server['id']
        
        # 检查服务器状态是否为在线
        if server['status'] == 'online':
            client = get_mcp_client(server_id)
            
            if client:
                # 尝试获取工具列表来测试连接状态
                try:
                    # 首先检查客户端的connected属性
                    if not client.connected:
                        util.log(1, f"服务器 {server['name']} (ID: {server_id}) 连接状态为断开，尝试重新连接...")
                        # 连接已断开，尝试重新连接
                        success, updated_server, tools = connect_to_real_mcp(server)
                        if success:
                            # 更新服务器信息
                            for i, s in enumerate(mcp_servers):
                                if s['id'] == server_id:
                                    mcp_servers[i] = updated_server
                                    reconnected_servers.append(updated_server['name'])
                                    break
                        continue
                    
                    # 尝试调用一个简单的工具来测试连接
                    test_success, test_result = client.call_tool("ping", {})
                    if not test_success:
                        util.log(1, f"服务器 {server['name']} (ID: {server_id}) 测试调用失败，尝试重新连接...")
                        # 调用失败，可能已断开连接，尝试重新连接
                        success, updated_server, tools = connect_to_real_mcp(server)
                        if success:
                            # 更新服务器信息
                            for i, s in enumerate(mcp_servers):
                                if s['id'] == server_id:
                                    mcp_servers[i] = updated_server
                                    reconnected_servers.append(updated_server['name'])
                                    break
                        continue
                    
                    # 如果工具调用成功但工具列表为空，也尝试重新连接
                    tools = client.list_tools()
                    if not tools:
                        # util.log(1, f"服务器 {server['name']} (ID: {server_id}) 工具列表为空，尝试重新连接...")
                        # 连接可能有问题，尝试重新连接
                        success, updated_server, tools = connect_to_real_mcp(server)
                        if success:
                            # 更新服务器信息
                            for i, s in enumerate(mcp_servers):
                                if s['id'] == server_id:
                                    mcp_servers[i] = updated_server
                                    reconnected_servers.append(updated_server['name'])
                                    break
                except Exception as e:
                    # util.log(1, f"检查服务器 {server['name']} (ID: {server_id}) 连接状态时出错: {e}")
                    # 连接出错，标记为离线并尝试重新连接
                    server['status'] = 'offline'
                    success, updated_server, tools = connect_to_real_mcp(server)
                    if success:
                        # 更新服务器信息
                        for i, s in enumerate(mcp_servers):
                            if s['id'] == server_id:
                                mcp_servers[i] = updated_server
                                reconnected_servers.append(updated_server['name'])
                                break
    
    # if reconnected_servers:
    #     util.log(1, f"已自动重新连接以下服务器: {', '.join(reconnected_servers)}")
    
    # 安排下一次检查
    schedule_connection_check()

# 安排连接检查定时任务
def schedule_connection_check():
    """
    安排下一次连接检查定时任务
    """
    global connection_check_timer
    
    # 取消现有定时器（如果有）
    if connection_check_timer:
        try:
            connection_check_timer.cancel()
        except:
            pass
    
    # 创建新的定时器
    connection_check_timer = threading.Timer(CONNECTION_CHECK_INTERVAL, check_mcp_connections)
    connection_check_timer.daemon = True  # 设置为守护线程，这样主程序退出时它会自动结束
    connection_check_timer.start()

# 启动连接检查
def start_connection_check():
    """
    启动MCP连接检查定时任务
    """
    util.log(1, "启动MCP连接状态检查定时任务...")
    schedule_connection_check()

# 主程序入口
def run():
    # 禁止服务器日志输出的类
    class NullLogHandler:
        def write(self, *args, **kwargs):
            pass
    
    # 使用gevent的pywsgi服务器，并禁用日志输出
    from gevent import pywsgi
    server = pywsgi.WSGIServer(
        ('0.0.0.0', 5010), 
        app,
        log=NullLogHandler()
    )
    server.serve_forever()

# 启动MCP服务器
def start():
    # 启动连接检查定时任务
    start_connection_check()

    
    # 输出启动信息
    util.log(1, "MCP服务已启动在端口5010")
    
    # 启动服务器
    from scheduler.thread_manager import MyThread
    MyThread(target=run).start()
