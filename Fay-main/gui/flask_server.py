import importlib
import json
import time
import os
import pyaudio
import re
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_cors import CORS
import requests
import datetime
import pytz
import logging
import uuid

import fay_booter
from tts import tts_voice
from gevent import pywsgi
from scheduler.thread_manager import MyThread
from utils import config_util, util
from core import wsa_server
from core import fay_core
from core import content_db
from core.interact import Interact
from core import member_db
import fay_booter
from flask_httpauth import HTTPBasicAuth
from core import qa_service
from core import stream_manager

# 全局变量，用于跟踪当前的genagents服务器
genagents_server = None
genagents_thread = None
monitor_thread = None

__app = Flask(__name__)
# 禁用 Flask 默认日志
__app.logger.disabled = True
log = logging.getLogger('werkzeug')
log.disabled = True
# 禁用请求日志中间件
__app.config['PROPAGATE_EXCEPTIONS'] = True

auth = HTTPBasicAuth()
CORS(__app, supports_credentials=True)

def load_users():
    try:
        with open('verifier.json') as f:
            users = json.load(f)
        return users
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

users = load_users()

@auth.verify_password
def verify_password(username, password):
    if not users or config_util.start_mode == 'common':
        return True
    if username in users and users[username] == password:
        return username


def __get_template():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error rendering template: {e}", 500

def __get_device_list():
    try:
        if config_util.start_mode == 'common':
            audio = pyaudio.PyAudio()
            device_list = []
            for i in range(audio.get_device_count()):
                devInfo = audio.get_device_info_by_index(i)
                if devInfo['hostApi'] == 0:
                    device_list.append(devInfo["name"])
            return list(set(device_list))
        else:
            return []
    except Exception as e:
        print(f"Error getting device list: {e}")
        return []

@__app.route('/api/submit', methods=['post'])
def api_submit():
    data = request.values.get('data')
    if not data:
        return jsonify({'result': 'error', 'message': '未提供数据'})
    try:
        config_data = json.loads(data)
        if 'config' not in config_data:
            return jsonify({'result': 'error', 'message': '数据中缺少config'})

        config_util.load_config()
        existing_config = config_util.config

        def merge_configs(existing, new):
            for key, value in new.items():
                if isinstance(value, dict) and key in existing:
                    if isinstance(existing[key], dict):
                        merge_configs(existing[key], value)
                    else:
                        existing[key] = value
                else:
                    existing[key] = value

        merge_configs(existing_config, config_data['config'])

        config_util.save_config(existing_config)
        config_util.load_config()

        return jsonify({'result': 'successful'})
    except json.JSONDecodeError:
        return jsonify({'result': 'error', 'message': '无效的JSON数据'})
    except Exception as e:
        return jsonify({'result': 'error', 'message': f'保存配置时出错: {e}'}), 500
    



@__app.route('/api/get-data', methods=['post'])
def api_get_data():
    # 获取配置和语音列表
    try:
        config_util.load_config()
        voice_list = tts_voice.get_voice_list()
        send_voice_list = []
        if config_util.tts_module == 'ali':
            voice_list = [
                {"id": "abin", "name": "阿斌"},
                {"id": "zhixiaobai", "name": "知小白"},
                {"id": "zhixiaoxia", "name": "知小夏"},
                {"id": "zhixiaomei", "name": "知小妹"},
                {"id": "zhigui", "name": "知柜"},
                {"id": "zhishuo", "name": "知硕"},
                {"id": "aixia", "name": "艾夏"},
                {"id": "zhifeng_emo", "name": "知锋_多情感"},
                {"id": "zhibing_emo", "name": "知冰_多情感"},
                {"id": "zhimiao_emo", "name": "知妙_多情感"},
                {"id": "zhimi_emo", "name": "知米_多情感"},
                {"id": "zhiyan_emo", "name": "知燕_多情感"},
                {"id": "zhibei_emo", "name": "知贝_多情感"},
                {"id": "zhitian_emo", "name": "知甜_多情感"},
                {"id": "xiaoyun", "name": "小云"},
                {"id": "xiaogang", "name": "小刚"},
                {"id": "ruoxi", "name": "若兮"},
                {"id": "siqi", "name": "思琪"},
                {"id": "sijia", "name": "思佳"},
                {"id": "sicheng", "name": "思诚"},
                {"id": "aiqi", "name": "艾琪"},
                {"id": "aijia", "name": "艾佳"},
                {"id": "aicheng", "name": "艾诚"},
                {"id": "aida", "name": "艾达"},
                {"id": "ninger", "name": "宁儿"},
                {"id": "ruilin", "name": "瑞琳"},
                {"id": "siyue", "name": "思悦"},
                {"id": "aiya", "name": "艾雅"},
                {"id": "aimei", "name": "艾美"},
                {"id": "aiyu", "name": "艾雨"},
                {"id": "aiyue", "name": "艾悦"},
                {"id": "aijing", "name": "艾婧"},
                {"id": "xiaomei", "name": "小美"},
                {"id": "aina", "name": "艾娜"},
                {"id": "yina", "name": "伊娜"},
                {"id": "sijing", "name": "思婧"},
                {"id": "sitong", "name": "思彤"},
                {"id": "xiaobei", "name": "小北"},
                {"id": "aitong", "name": "艾彤"},
                {"id": "aiwei", "name": "艾薇"},
                {"id": "aibao", "name": "艾宝"},
                {"id": "shanshan", "name": "姗姗"},
                {"id": "chuangirl", "name": "小玥"},
                {"id": "lydia", "name": "Lydia"},
                {"id": "aishuo", "name": "艾硕"},
                {"id": "qingqing", "name": "青青"},
                {"id": "cuijie", "name": "翠姐"},
                {"id": "xiaoze", "name": "小泽"},
                {"id": "zhimao", "name": "知猫"},
                {"id": "zhiyuan", "name": "知媛"},
                {"id": "zhiya", "name": "知雅"},
                {"id": "zhiyue", "name": "知悦"},
                {"id": "zhida", "name": "知达"},
                {"id": "zhistella", "name": "知莎"},
                {"id": "kelly", "name": "Kelly"},
                {"id": "jiajia", "name": "佳佳"},
                {"id": "taozi", "name": "桃子"},
                {"id": "guijie", "name": "柜姐"},
                {"id": "stella", "name": "Stella"},
                {"id": "stanley", "name": "Stanley"},
                {"id": "kenny", "name": "Kenny"},
                {"id": "rosa", "name": "Rosa"},
                {"id": "mashu", "name": "马树"},
                {"id": "xiaoxian", "name": "小仙"},
                {"id": "yuer", "name": "悦儿"},
                {"id": "maoxiaomei", "name": "猫小美"},
                {"id": "aifei", "name": "艾飞"},
                {"id": "yaqun", "name": "亚群"},
                {"id": "qiaowei", "name": "巧薇"},
                {"id": "dahu", "name": "大虎"},
                {"id": "ailun", "name": "艾伦"},
                {"id": "jielidou", "name": "杰力豆"},
                {"id": "laotie", "name": "老铁"},
                {"id": "laomei", "name": "老妹"},
                {"id": "aikan", "name": "艾侃"}
            ]
            send_voice_list = {"voiceList": voice_list}
            wsa_server.get_web_instance().add_cmd(send_voice_list)
        elif config_util.tts_module == 'volcano':
            voice_list = [
                {"id": "BV001_streaming", "name": "通用女声"},
                {"id": "BV002_streaming", "name": "通用男声"},
                {"id": "zh_male_jingqiangkanye_moon_bigtts", "name": "京腔侃爷/Harmony"},
                {"id": "zh_female_shuangkuaisisi_moon_bigtts", "name": "爽快思思/Skye"},
                {"id": "zh_male_wennuanahu_moon_bigtts", "name": "温暖阿虎/Alvin"},
                {"id": "zh_female_wanwanxiaohe_moon_bigtts", "name": "湾湾小何"}
            ]
            send_voice_list = {"voiceList": voice_list}
            wsa_server.get_web_instance().add_cmd(send_voice_list)

        else:
            voice_list = tts_voice.get_voice_list()
            send_voice_list = []
            for voice in voice_list:
                voice_data = voice.value
                send_voice_list.append({"id": voice_data['name'], "name": voice_data['name']})
            wsa_server.get_web_instance().add_cmd({"voiceList": send_voice_list})
            voice_list = send_voice_list
        wsa_server.get_web_instance().add_cmd({"deviceList": __get_device_list()})
        if fay_booter.is_running():
            wsa_server.get_web_instance().add_cmd({"liveState": 1})
        return json.dumps({'config': config_util.config, 'voice_list': voice_list})
    except Exception as e:
        return jsonify({'result': 'error', 'message': f'获取数据时出错: {e}'}), 500

@__app.route('/api/start-live', methods=['post'])
def api_start_live():
    # 启动
    try:
        fay_booter.start()
        time.sleep(1)
        wsa_server.get_web_instance().add_cmd({"liveState": 1})
        return '{"result":"successful"}'
    except Exception as e:
        return jsonify({'result': 'error', 'message': f'启动时出错: {e}'}), 500

@__app.route('/api/stop-live', methods=['post'])
def api_stop_live():
    # 停止
    try:
        fay_booter.stop()
        time.sleep(1)
        wsa_server.get_web_instance().add_cmd({"liveState": 0})
        return '{"result":"successful"}'
    except Exception as e:
        return jsonify({'result': 'error', 'message': f'停止时出错: {e}'}), 500

@__app.route('/api/send', methods=['post'])
def api_send():
    # 接收前端发送的消息
    data = request.values.get('data')
    if not data:
        return jsonify({'result': 'error', 'message': '未提供数据'})
    try:
        info = json.loads(data)
        username = info.get('username')
        msg = info.get('msg')
        if not username or not msg:
            return jsonify({'result': 'error', 'message': '用户名和消息内容不能为空'})
        msg = msg.strip()
        interact = Interact("text", 1, {'user': username, 'msg': msg})
        util.printInfo(1, username, '[文字发送按钮]{}'.format(interact.data["msg"]), time.time())
        fay_booter.feiFei.on_interact(interact)
        return '{"result":"successful"}'
    except json.JSONDecodeError:
        return jsonify({'result': 'error', 'message': '无效的JSON数据'})
    except Exception as e:
        return jsonify({'result': 'error', 'message': f'发送消息时出错: {e}'}), 500

# 获取指定用户的消息记录
@__app.route('/api/get-msg', methods=['post'])
def api_get_Msg():
    try:
        data = request.form.get('data')
        if data is None:
            data = request.get_json()
        else:
            data = json.loads(data)
        uid = member_db.new_instance().find_user(data["username"])
        contentdb = content_db.new_instance()
        if uid == 0:
            return json.dumps({'list': []})
        else:
            list = contentdb.get_list('all', 'desc', 1000, uid)
        relist = []
        i = len(list) - 1
        while i >= 0:
            timezone = pytz.timezone('Asia/Shanghai')
            timetext = datetime.datetime.fromtimestamp(list[i][3], timezone).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            relist.append(dict(type=list[i][0], way=list[i][1], content=list[i][2], createtime=list[i][3], timetext=timetext, username=list[i][5], id=list[i][6], is_adopted=list[i][7]))
            i -= 1
        if fay_booter.is_running():
            wsa_server.get_web_instance().add_cmd({"liveState": 1})
        return json.dumps({'list': relist})
    except json.JSONDecodeError:
        return jsonify({'list': [], 'message': '无效的JSON数据'})
    except Exception as e:
        return jsonify({'list': [], 'message': f'获取消息时出错: {e}'}), 500

@__app.route('/v1/chat/completions', methods=['post'])
@__app.route('/api/send/v1/chat/completions', methods=['post'])
def api_send_v1_chat_completions():
    # 处理聊天完成请求
    data = request.get_json()
    if not data:
        return jsonify({'error': '未提供数据'})
    try:
        last_content = ""
        if 'messages' in data and data['messages']:
            last_message = data['messages'][-1]
            username = last_message.get('role', 'User')
            if username == 'user':
                username = 'User'
            last_content = last_message.get('content', 'No content provided')
        else:
            last_content = 'No messages found'
            username = 'User'

        model = data.get('model', 'fay')
        observation = data.get('observation', '')
        interact = Interact("text", 1, {'user': username, 'msg': last_content, 'observation': str(observation)})
        util.printInfo(1, username, '[文字沟通接口]{}'.format(interact.data["msg"]), time.time())
        fay_booter.feiFei.on_interact(interact)

        # 检查请求中是否指定了流式传输
        stream_requested = data.get('stream', False)
        
        # 优先使用请求中的stream参数，如果没有指定则使用配置中的设置
        if stream_requested or model == 'fay-streaming':
            return gpt_stream_response(last_content, username)
        else:
            return non_streaming_response(last_content, username)
    except Exception as e:
        return jsonify({'error': f'处理请求时出错: {e}'}), 500

@__app.route('/api/get-member-list', methods=['post'])
def api_get_Member_list():
    # 获取成员列表
    try:
        memberdb = member_db.new_instance()
        list = memberdb.get_all_users()
        return json.dumps({'list': list})
    except Exception as e:
        return jsonify({'list': [], 'message': f'获取成员列表时出错: {e}'}), 500

@__app.route('/api/get-run-status', methods=['post'])
def api_get_run_status():
    # 获取运行状态
    try:
        status = fay_booter.is_running()
        return json.dumps({'status': status})
    except Exception as e:
        return jsonify({'status': False, 'message': f'获取运行状态时出错: {e}'}), 500

@__app.route('/api/adopt-msg', methods=['POST'])
def adopt_msg():
    # 采纳消息
    data = request.get_json()
    if not data:
        return jsonify({'status':'error', 'msg': '未提供数据'})

    id = data.get('id')

    if not id:
        return jsonify({'status':'error', 'msg': 'id不能为空'})

    if  config_util.config["interact"]["QnA"] == "":
        return jsonify({'status':'error', 'msg': '请先设置Q&A文件'})

    try:
        info = content_db.new_instance().get_content_by_id(id)
        content = info[3] if info else ''
        if info is not None:
            previous_info = content_db.new_instance().get_previous_user_message(id)
            previous_content = previous_info[3] if previous_info else ''
            result = content_db.new_instance().adopted_message(id)
            if result:
                qa_service.QAService().record_qapair(previous_content, content)
                return jsonify({'status': 'success', 'msg': '采纳成功'})
            else:
                return jsonify({'status':'error', 'msg': '采纳失败'}), 500
        else:
            return jsonify({'status':'error', 'msg': '消息未找到'}), 404
    except Exception as e:
        return jsonify({'status':'error', 'msg': f'采纳消息时出错: {e}'}), 500

def gpt_stream_response(last_content, username):
    _, nlp_Stream = stream_manager.new_instance().get_Stream(username)
    def generate():
        while True:
            sentence = nlp_Stream.read()
            if sentence is None:
                time.sleep(0.01)
                continue
            
            # 处理特殊标记
            is_first = "_<isfirst>" in sentence
            is_end = "_<isend>" in sentence
            content = sentence.replace("_<isfirst>", "").replace("_<isend>", "")
            if content or is_first or is_end:  # 只有当有实际内容时才发送
                message = {
                    "id": "faystreaming-" + str(uuid.uuid4()),
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "fay-streaming",
                    "choices": [
                        {
                            "delta": {
                                "content": content
                            },
                            "index": 0,
                            "finish_reason": "stop" if is_end else None
                        }
                    ],
                    #TODO 这里的token计算方式需要优化
                    "usage": {
                        "prompt_tokens": len(last_content) if is_first else 0, 
                        "completion_tokens": len(content),
                        "total_tokens": len(last_content) + len(content)
                    },
                    "system_fingerprint": ""
                }
                if is_end:
                    if username in fay_booter.feiFei.nlp_streams:
                        stream_manager.new_instance().clear_Stream(username)
                yield f"data: {json.dumps(message)}\n\n"
            if is_end:
                break
            time.sleep(0.01)
        yield 'data: [DONE]\n\n'
    
    return Response(generate(), mimetype='text/event-stream')

# 处理非流式响应
def non_streaming_response(last_content, username):
    _, nlp_Stream = stream_manager.new_instance().get_Stream(username)
    text = ""
    while True:
        sentence = nlp_Stream.read()
        if sentence is None:
            time.sleep(0.01)
            continue
        
        # 处理特殊标记
        is_first = "_<isfirst>" in sentence
        is_end = "_<isend>" in sentence
        text += sentence.replace("_<isfirst>", "").replace("_<isend>", "")
        if is_end:
            if username in fay_booter.feiFei.nlp_streams:
                stream_manager.new_instance().clear_Stream(username)
            break
    return jsonify({
        "id": "fay-" + str(uuid.uuid4()),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "fay",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text
                },
                "logprobs": "",
                "finish_reason": "stop"
            }
        ],
        #TODO 这里的token计算方式需要优化
        "usage": {
            "prompt_tokens": len(last_content), 
            "completion_tokens": len(text),
            "total_tokens": len(last_content) + len(text)
        },
        "system_fingerprint": ""
    })

@__app.route('/', methods=['get'])
@auth.login_required
def home_get():
    try:
        return __get_template()
    except Exception as e:
        return f"Error loading home page: {e}", 500

@__app.route('/', methods=['post'])
@auth.login_required
def home_post():
    try:
        return __get_template()
    except Exception as e:
        return f"Error processing request: {e}", 500

@__app.route('/setting', methods=['get'])
def setting():
    try:
        return render_template('setting.html')
    except Exception as e:
        return f"Error loading settings page: {e}", 500

@__app.route('/Page3', methods=['get'])
def Page3():
    try:
        return render_template('Page3.html')
    except Exception as e:
        return f"Error loading settings page: {e}", 500


# 输出的音频http
@__app.route('/audio/<filename>')
def serve_audio(filename):
    audio_file = os.path.join(os.getcwd(), "samples", filename)
    if os.path.exists(audio_file):
        return send_file(audio_file)
    else:
        return jsonify({'error': '文件未找到'}), 404

# 输出的表情gif
@__app.route('/robot/<filename>')
def serve_gif(filename):
    gif_file = os.path.join(os.getcwd(), "gui", "robot", filename)
    if os.path.exists(gif_file):
        return send_file(gif_file)
    else:
        return jsonify({'error': '文件未找到'}), 404

#打招呼
@__app.route('/to-greet', methods=['POST'])
def to_greet():
    data = request.get_json()
    username = data.get('username', 'User')
    observation = data.get('observation', '')
    interact = Interact("hello", 1, {'user': username, 'msg': '按观测要求打个招呼', 'observation': str(observation)})
    text = fay_booter.feiFei.on_interact(interact)
    return jsonify({'status': 'success', 'data': text, 'msg': '已进行打招呼'}), 200 

#唤醒:在普通唤醒模式，进行大屏交互才有意义
@__app.route('/to-wake', methods=['POST'])
def to_wake():
    data = request.get_json()
    username = data.get('username', 'User')
    observation = data.get('observation', '')
    fay_booter.recorderListener.wakeup_matched = True
    return jsonify({'status': 'success', 'msg': '已唤醒'}), 200 

#打断
@__app.route('/to-stop-talking', methods=['POST'])
def to_stop_talking():
    try:
        data = request.get_json()
        username = data.get('username', 'User')
        message = data.get('text', '你好，请说？')
        observation = data.get('observation', '')
        interact = Interact("stop_talking", 2, {'user': username, 'text': message, 'observation': str(observation)})
        result = fay_booter.feiFei.on_interact(interact)
        return jsonify({
            'status': 'success',
            'data': str(result) if result is not None else '',
            'msg': '已停止说话'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'msg': str(e)
        }), 500


#消息透传接口
@__app.route('/transparent-pass', methods=['post'])
def transparent_pass():
    try:
        data = request.form.get('data')
        if data is None:
            data = request.get_json()
        else:
            data = json.loads(data)
        user = data.get('user', 'User')
        response_text = data.get('text', '')
        audio_url = data.get('audio', '')
        interact = Interact('transparent_pass', 2, {'user': user, 'text': response_text, 'audio': audio_url})
        util.printInfo(1, user, '透传播放：{}，{}'.format(response_text, audio_url), time.time())
        success = fay_booter.feiFei.on_interact(interact)
        if (success == 'success'):
            return jsonify({'code': 200, 'message' : '成功'})
        return jsonify({'code': 500, 'message' : '未错原因出错'})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'出错: {e}'}), 500

# 清除记忆API
@__app.route('/api/clear-memory', methods=['POST'])
def api_clear_memory():
    try:
        # 获取memory目录路径
        memory_dir = os.path.join(os.getcwd(), "memory")
        
        # 检查目录是否存在
        if not os.path.exists(memory_dir):
            return jsonify({'success': False, 'message': '记忆目录不存在'}), 400
        
        # 清空memory目录下的所有文件（保留目录结构）
        for root, dirs, files in os.walk(memory_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        util.log(1, f"已删除文件: {file_path}")
                except Exception as e:
                    util.log(1, f"删除文件时出错: {file_path}, 错误: {str(e)}")
        
        # 删除memory_dir下的所有子目录
        import shutil
        for item in os.listdir(memory_dir):
            item_path = os.path.join(memory_dir, item)
            if os.path.isdir(item_path):
                try:
                    shutil.rmtree(item_path)
                    util.log(1, f"已删除目录: {item_path}")
                except Exception as e:
                    util.log(1, f"删除目录时出错: {item_path}, 错误: {str(e)}")
        
        # 创建一个标记文件，表示记忆已被清除，防止退出时重新保存
        with open(os.path.join(memory_dir, ".memory_cleared"), "w") as f:
            f.write("Memory has been cleared. Do not save on exit.")
        
        # 设置记忆清除标记
        try:
            # 导入并修改nlp_cognitive_stream模块中的保存函数
            from llm.nlp_cognitive_stream import set_memory_cleared_flag, clear_agent_memory
            
            # 设置记忆清除标记
            set_memory_cleared_flag(True)
            
            # 清除内存中已加载的记忆
            clear_agent_memory()
            
            util.log(1, "已同时清除文件存储和内存中的记忆")
        except Exception as e:
            util.log(1, f"清除内存中记忆时出错: {str(e)}")
        
        util.log(1, "记忆已清除，需要重启应用才能生效")
        return jsonify({'success': True, 'message': '记忆已清除，请重启应用使更改生效'}), 200
    except Exception as e:
        util.log(1, f"清除记忆时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'清除记忆时出错: {str(e)}'}), 500

# 启动genagents_flask.py的API
@__app.route('/api/start-genagents', methods=['POST'])
def api_start_genagents():
    try:
        # 只有在数字人启动后才能克隆人格
        if not fay_booter.is_running():
            return jsonify({'success': False, 'message': 'Fay未启动，无法启动决策分析'}), 400
        
        # 获取克隆要求
        data = request.get_json()
        if not data or 'instruction' not in data:
            return jsonify({'success': False, 'message': '缺少克隆要求参数'}), 400
        
        instruction = data['instruction']
        
        # 保存指令到临时文件，供genagents_flask.py读取
        instruction_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'genagents', 'instruction.json')
        with open(instruction_file, 'w', encoding='utf-8') as f:
            json.dump({'instruction': instruction}, f, ensure_ascii=False)
        
        # 导入genagents_flask模块
        import sys
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        from genagents.genagents_flask import start_genagents_server, is_shutdown_requested
        from werkzeug.serving import make_server
        
        # 关闭之前的genagents服务器（如果存在）
        global genagents_server, genagents_thread, monitor_thread
        if genagents_server is not None:
            try:
                # 主动关闭之前的服务器
                util.log(1, "关闭之前的决策分析服务...")
                genagents_server.shutdown()
                # 等待线程结束
                if genagents_thread and genagents_thread.is_alive():
                    genagents_thread.join(timeout=2)
                if monitor_thread and monitor_thread.is_alive():
                    monitor_thread.join(timeout=2)
            except Exception as e:
                util.log(1, f"关闭之前的决策分析服务时出错: {str(e)}")
        
        # 清除之前的记忆，确保只保留最新的决策分析
        try:
            from llm.nlp_cognitive_stream import clear_agent_memory
            util.log(1, "已清除之前的决策分析记忆")
        except Exception as e:
            util.log(1, f"清除之前的决策分析记忆时出错: {str(e)}")
        
        # 启动决策分析服务（不启动单独进程，而是返回Flask应用实例）
        genagents_app = start_genagents_server(instruction_text=instruction)
        
        # 创建服务器
        genagents_server = make_server('0.0.0.0', 5001, genagents_app)
        
        # 在后台线程中启动Flask服务
        import threading
        def run_genagents_app():
            try:
                # 使用serve_forever而不是app.run
                genagents_server.serve_forever()
            except Exception as e:
                util.log(1, f"决策分析服务运行出错: {str(e)}")
            finally:
                util.log(1, f"决策分析服务已关闭")
        
        # 启动监控线程，检查是否需要关闭服务器
        def monitor_shutdown():
            try:
                while not is_shutdown_requested():
                    time.sleep(1)
                util.log(1, f"检测到关闭请求，正在关闭决策分析服务...")
                genagents_server.shutdown()
            except Exception as e:
                util.log(1, f"监控决策分析服务时出错: {str(e)}")
        
        # 启动服务器线程
        genagents_thread = threading.Thread(target=run_genagents_app)
        genagents_thread.daemon = True
        genagents_thread.start()
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=monitor_shutdown)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        util.log(1, f"已启动决策分析页面，指令: {instruction}")
        
        # 返回决策分析页面的URL
        return jsonify({
            'success': True, 
            'message': '已启动决策分析页面',
            'url': 'http://127.0.0.1:5001/'
        }), 200
    except Exception as e:
        util.log(1, f"启动决策分析页面时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'启动决策分析页面时出错: {str(e)}'}), 500

def run():
    class NullLogHandler:
        def write(self, *args, **kwargs):
            pass
    server = pywsgi.WSGIServer(
        ('0.0.0.0', 5000), 
        __app,
        log=NullLogHandler()  
    )
    server.serve_forever()

def start():
    MyThread(target=run).start()
