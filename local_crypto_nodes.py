import json
import os
import random
import uuid
import torch
import base64
import folder_paths
from comfy_execution.graph import ExecutionBlocker
from comfy_execution.graph_utils import GraphBuilder
from server import PromptServer
from .local_crypto import LocalCryptoWorkflow
from .utils import get_crypto_workflow_dir


class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


any = AnyType("*")


class AlwaysEqualProxy(str):
    def __eq__(self, _):
        return True

    def __ne__(self, _):
        return False


class AlwaysTupleZero(tuple):
    def __getitem__(self, _):
        return AlwaysEqualProxy(super().__getitem__(0))


# 检查并确保目录存在
def ensure_directory_exists(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            print(f"创建目录: {path}")
            return True
        except Exception as e:
            print(f"创建目录失败: {path}, 错误: {str(e)}")
            return False
    return True


def get_crypto_workflow_dir():
    """获取加密工作流目录"""
    base_dir = os.path.dirname(folder_paths.output_directory)
    crypto_dir = os.path.join(base_dir, "crypto-workflow")
    ensure_directory_exists(crypto_dir)
    return crypto_dir


class ChenYuSaveLocalCryptoNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "template_id": ("STRING", {"default": uuid.uuid4().hex}),
                "password": ("STRING", {"default": ""}),
                "add_input": ("BOOLEAN", {"default": False, "label_on": "添加", "label_off": "添加"}),
            },
            "optional": {"input_anything": (any,)},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "crypto"
    CATEGORY = "advanced/晨羽节点加密"

    @classmethod
    def IS_CHANGED(s, **kwargs):
        add_input = kwargs.get("add_input", False)
        if add_input:
            return random.random()
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(s, input_types):
        return True
        
    @classmethod
    def onNodeCreated(cls, prompt_id):
        return {"inputs": ["input_anything"]}
    
    @classmethod
    def onConnected(cls, node_id, input_name, output_id, output_name, prompt):
        inputs = prompt[node_id].get("inputs", {})
        input_anything_keys = [k for k in inputs.keys() if k.startswith("input_anything")]
        
        if not input_anything_keys:
            return {"update_inputs": ["input_anything"]}
            
        if input_name == input_anything_keys[-1]:
            max_index = 0
            for key in input_anything_keys:
                if key == "input_anything":
                    continue
                try:
                    index = int(key.replace("input_anything", ""))
                    max_index = max(max_index, index)
                except:
                    pass
            
            new_input = f"input_anything{max_index + 1}"
            prompt[node_id]["inputs"][new_input] = None
            return {"update_inputs": [new_input]}
        return {}
        
    @classmethod
    def getExecutionInputs(cls, execution_inputs):
        if not execution_inputs:
            return None
        execution_inputs = execution_inputs.copy()
        result = {}
        for k, v in execution_inputs.items():
            if k.startswith("input_anything"):
                result[k] = v
        return result

    def crypto(self, template_id, password, add_input=False, **kwargs):
        # 如果点击了添加按钮，不执行实际操作
        if add_input:
            return (ExecutionBlocker(None),)

        # 对密码进行加盐处理
        salt = template_id[:8]  # 使用template_id的前8位作为盐值
        salted_password = f"{password}_{salt}"  # 简单的加盐方式

        unique_id = kwargs.pop("unique_id", None)
        prompt = kwargs.pop("prompt", None)
        extra_pnginfo = kwargs.pop("extra_pnginfo", None)
        
        if unique_id is None:
            raise Exception("Warning: 'unique_id' is missing.")
        if prompt is None:
            raise Exception("Warning: 'prompt' is missing.")
        if len(template_id) != 32:
            raise Exception("Warning: 'template_id' length is not 32.")
        if not password:
            raise Exception("Warning: 密码不能为空.")
        
        # 确保输出目录存在
        output_dir = get_crypto_workflow_dir()
        temp_dir = folder_paths.temp_directory
        
        if not ensure_directory_exists(output_dir):
            raise Exception(f"无法创建输出目录: {output_dir}")
        if not ensure_directory_exists(temp_dir):
            raise Exception(f"无法创建临时目录: {temp_dir}")
            
        # 调试信息
        print(f"===== 开始加密工作流 =====")
        print(f"Template ID: {template_id}")
        print(f"加密工作流目录: {output_dir}")
        print(f"ComfyUI临时目录: {temp_dir}")
        
        # 初始化加密工作流处理器
        crypto_workflow = LocalCryptoWorkflow(extra_pnginfo["workflow"], prompt, template_id)
        
        try:
            # 按照原始加密节点的处理流程
            crypto_workflow.invalid_workflow()
            crypto_workflow.load_workflow()
            crypto_workflow.load_prompt()
            crypto_workflow.analysis_node()
            
            # 计算加密结果并保存到临时文件
            crypto_dir = crypto_workflow.calculate_crypto_result(f"crypto_{template_id}.json")
            
            # 生成简化的工作流
            output_dir = crypto_workflow.output_workflow_simple_shell(f"local_crypto_workflow_{template_id}.json")
            
            # 生成加密的二进制文件
            encrypted_data = crypto_workflow.encrypt_workflow(salted_password)
            if encrypted_data is None:
                raise Exception("加密工作流数据失败")
            
            # 保存加密数据到输出目录
            encrypted_file_path = os.path.join(output_dir, f"local_crypto_{template_id}.bin")
            with open(encrypted_file_path, "wb") as f:
                f.write(encrypted_data)
                
            print(f"成功保存加密数据到: {encrypted_file_path}")
            print(f"===== 完成加密工作流 =====")
            
            # 发送成功通知
            PromptServer.instance.send_sync(
                "cryptocat_toast", 
                {
                    "content": f"工作流加密成功!\n文件保存在: {encrypted_file_path}", 
                    "type": "success", 
                    "duration": 8000
                }
            )
            
            return (ExecutionBlocker(None),)
            
        except Exception as e:
            error_msg = f"加密工作流失败: {str(e)}"
            print(error_msg)
            PromptServer.instance.send_sync(
                "cryptocat_toast", 
                {"content": error_msg, "type": "error", "duration": 8000}
            )
            return (ExecutionBlocker(None),)


class ChenYuLocalCryptoBridgeNode:
    """桥接节点，标记加密区域的结束"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"value": (any,)}}

    @classmethod
    def VALIDATE_INPUTS(s, input_types):
        return True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    RETURN_TYPES = (any,)
    RETURN_NAMES = ("output",)
    FUNCTION = "bridge"
    CATEGORY = "advanced/晨羽节点加密"

    def bridge(self, value):
        return (value,)


def is_link(value):
    """判断值是否为链接格式"""
    if not isinstance(value, list):
        return False
    if len(value) != 2:
        return False
    if not isinstance(value[0], (str, int)):
        return False
    if not isinstance(value[1], int):
        return False
    return True


class ChenYuLocalDecodeCryptoNode:
    """本地解密节点，使用密码解密并执行工作流"""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "template_id": ("STRING", {"default": ""}),
                "password": ("STRING", {"default": ""}),
                "add_input": ("BOOLEAN", {"default": False, "label_on": "添加", "label_off": "添加"}),
            },
            "optional": {"input_anything": (any,)},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = AlwaysTupleZero(AlwaysEqualProxy("*"))
    RETURN_NAMES = ("output",)
    FUNCTION = "decode"
    CATEGORY = "advanced/晨羽节点加密"

    @classmethod
    def IS_CHANGED(s, **kwargs):
        add_input = kwargs.get("add_input", False)
        if add_input:
            return random.random()
        return float("NaN")
        
    @classmethod
    def onNodeCreated(cls, prompt_id):
        return {"inputs": ["input_anything"]}
    
    @classmethod
    def onConnected(cls, node_id, input_name, output_id, output_name, prompt):
        inputs = prompt[node_id].get("inputs", {})
        input_anything_keys = [k for k in inputs.keys() if k.startswith("input_anything")]
        
        if not input_anything_keys:
            return {"update_inputs": ["input_anything"]}
            
        if input_name == input_anything_keys[-1]:
            max_index = 0
            for key in input_anything_keys:
                if key == "input_anything":
                    continue
                try:
                    index = int(key.replace("input_anything", ""))
                    max_index = max(max_index, index)
                except:
                    pass
            
            new_input = f"input_anything{max_index + 1}"
            prompt[node_id]["inputs"][new_input] = None
            return {"update_inputs": [new_input]}
        return {}
        
    @classmethod
    def getExecutionInputs(cls, execution_inputs):
        if not execution_inputs:
            return None
        execution_inputs = execution_inputs.copy()
        result = {}
        for k, v in execution_inputs.items():
            if k.startswith("input_anything"):
                result[k] = v
        return result

    def decode(self, template_id, password, add_input=False, **kwargs):
        # 如果点击了添加按钮，不执行实际操作
        if add_input:
            return {"result": tuple([None]), "expand": {}}
        
        if not template_id:
            raise Exception("Warning: template_id 不能为空.")
        if not password:
            raise Exception("Warning: 密码不能为空.")
        
        # 对密码进行加盐处理
        salt = template_id[:8]  # 使用template_id的前8位作为盐值
        salted_password = f"{password}_{salt}"  # 简单的加盐方式

        # 确保输出目录存在
        output_dir = get_crypto_workflow_dir()
        temp_dir = folder_paths.temp_directory
        
        if not ensure_directory_exists(output_dir):
            raise Exception(f"无法创建输出目录: {output_dir}")
        if not ensure_directory_exists(temp_dir):
            raise Exception(f"无法创建临时目录: {temp_dir}")
            
        print(f"===== 开始解密工作流 =====")
        print(f"Template ID: {template_id}")
        print(f"加密工作流目录: {output_dir}")
        print(f"ComfyUI临时目录: {temp_dir}")
        
        try:
            # 查找加密文件
            encrypted_file_paths = [
                os.path.join(output_dir, f"local_crypto_{template_id}.bin"),
                os.path.join(temp_dir, f"local_crypto_{template_id}.bin")
            ]
            
            encrypted_file_path = None
            for path in encrypted_file_paths:
                if os.path.exists(path):
                    encrypted_file_path = path
                    break
                    
            if not encrypted_file_path:
                encrypted_paths_str = "\n".join(encrypted_file_paths)
                raise Exception(f"加密文件未找到，已检查以下路径:\n{encrypted_paths_str}")
                
            print(f"找到加密文件: {encrypted_file_path}")
                
            # 读取加密数据
            with open(encrypted_file_path, "rb") as f:
                encrypted_data = f.read()
                
            print(f"读取加密数据，大小: {len(encrypted_data)} 字节")
                
            # 解密数据
            decrypted_data = LocalCryptoWorkflow.decrypt_workflow(encrypted_data, salted_password)
            if not decrypted_data:
                raise Exception("解密失败，请检查密码是否正确")
                
            print(f"解密成功")
            
            # 构建执行图
            processed_nodes = {}
            graph = GraphBuilder()
            
            # 收集input_anything映射
            input_anything_map = {}
            for node_id, node in kwargs.get("prompt", {}).items():
                if node.get("class_type") == "ChenYuLocalDecodeCryptoNode":
                    for input_name, input_value in node.get("inputs", {}).items():
                        if input_name.startswith("input_anything") and is_link(input_value):
                            key = f"{input_value[0]}_{input_value[1]}"
                            input_anything_map[key] = input_name
            
            def get_node_result(node_data, id):
                """递归构建节点执行图"""
                # 处理所有输入依赖
                input_keys = []
                for ikey in node_data["inputs"].keys():
                    input_value = node_data["inputs"][ikey]
                    if (
                        is_link(input_value) 
                        and get_hidden_input(input_value) is None
                        and str(input_value[0]) not in processed_nodes
                        and str(input_value[0]) in decrypted_data["prompt"]
                    ):
                        input_keys.append(str(input_value[0]))
                        
                # 递归处理依赖节点
                for ikey in input_keys:
                    if ikey not in decrypted_data["prompt"]:
                        continue
                    node = get_node_result(decrypted_data["prompt"][ikey], ikey)
                    processed_nodes[ikey] = node
                
                # 处理当前节点的输入
                inputs = node_data["inputs"]
                new_inputs = {}
                for ikey in inputs.keys():
                    if is_link(inputs[ikey]):
                        # 检查是否为外部输入
                        hidden_input_name = get_hidden_input(inputs[ikey])
                        if hidden_input_name and hidden_input_name in kwargs:
                            new_inputs[ikey] = kwargs[hidden_input_name]
                        # 否则从处理过的节点获取输出
                        elif str(inputs[ikey][0]) in processed_nodes:
                            new_inputs[ikey] = processed_nodes[str(inputs[ikey][0])].out(inputs[ikey][1])
                    else:
                        new_inputs[ikey] = inputs[ikey]
                        
                # 创建并返回节点
                return graph.node(node_data["class_type"], id, **new_inputs)
            
            def get_hidden_input(input_value):
                """获取隐藏输入名称"""
                if is_link(input_value):
                    key = f"{input_value[0]}_{input_value[1]}"
                    return input_anything_map.get(key, None)
                return None
            
            # 获取输出节点信息
            node_id, link_idx = decrypted_data["outputs"]
            if str(node_id) not in decrypted_data["prompt"]:
                raise Exception(f"输出节点 {node_id} 在解密数据中不存在")
                
            print(f"开始执行加密的节点，输出节点ID: {node_id}")
                
            # 构建并执行节点图
            node_data = decrypted_data["prompt"][str(node_id)]
            node = get_node_result(node_data, str(node_id))
            value = node.out(link_idx)
            
            print(f"===== 完成解密和执行工作流 =====")
            
            return {"result": tuple([value]), "expand": graph.finalize()}
        except Exception as e:
            error_msg = f"解密工作流失败: {str(e)}"
            print(error_msg)
            PromptServer.instance.send_sync(
                "cryptocat_toast", 
                {"content": error_msg, "type": "error", "duration": 8000}
            )
            return {"result": tuple([None]), "expand": {}} 