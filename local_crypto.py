import json
import os
import zlib
import uuid
import pyzipper
from io import BytesIO
import folder_paths
from collections import defaultdict
import copy
from .file_compressor import FileCompressor


class LocalCryptoWorkflow:
    def __init__(self, workflow, prompt, template_id=None):
        self.workflow = copy.deepcopy(workflow)
        self.prompt = copy.deepcopy(prompt)
        self.template_id = template_id or uuid.uuid4().hex
        self.workflow_nodes_dict = {}
        self.link_owner_map = defaultdict(dict)
        self.node_prompt_map = {}
        self.last_node_id = 0
        self.last_link_id = 0
        self.save_crypto_node_id = 0
        self.crypto_bridge_node_id = 0
        self.input_nodes_ids = set()
        self.output_nodes_ids = set()
        self.crypto_nodes_ids = set()
        self.crypto_result = {"prompt": {}, "workflow": {}, "outputs": []}
    
    def invalid_workflow(self):
        """验证工作流合法性"""
        for node in self.workflow["nodes"]:
            node_type = node.get("type", "")
            if node_type == "ChenYuLocalCryptoBridgeNode":
                if self.crypto_bridge_node_id == 0:
                    self.crypto_bridge_node_id = int(node["id"])
                else:
                    raise ValueError("Error: 在工作流中找到多个 'ChenYuLocalCryptoBridgeNode'")
                continue
            elif node_type == "ChenYuSaveLocalCryptoNode":
                if self.save_crypto_node_id == 0:
                    self.save_crypto_node_id = int(node["id"])
                else:
                    raise ValueError("Error: 在工作流中找到多个 'ChenYuSaveLocalCryptoNode'")
                continue
        if self.save_crypto_node_id == 0:
            raise ValueError("Error: 工作流中未找到 'ChenYuSaveLocalCryptoNode'")
        if self.crypto_bridge_node_id == 0:
            raise ValueError("Error: 工作流中未找到 'ChenYuLocalCryptoBridgeNode'")
            
    def load_workflow(self):
        """加载工作流结构"""
        self.workflow_nodes_dict = {
            int(node["id"]): node for node in self.workflow["nodes"]
        }
        for node in self.workflow["nodes"]:
            output_nodes = node.get("outputs", [])
            if not output_nodes:
                continue
            for output in output_nodes:
                links = output.get("links", [])
                if not links:
                    continue
                for link in links:
                    link = int(link)
                    self.link_owner_map[link]["links"] = copy.deepcopy(links)
                    self.link_owner_map[link]["slot_index"] = output.get(
                        "slot_index", 0
                    )
                    self.link_owner_map[link]["owner_id"] = int(node["id"])
                    self.link_owner_map[link]["type"] = output.get("type", "")
        self.last_node_id = int(self.workflow.get("last_node_id", 0))
        self.last_link_id = int(self.workflow.get("last_link_id", 0))
        
    def load_prompt(self):
        """加载节点配置"""
        self.node_prompt_map = {
            int(node_id): node for (node_id, node) in self.prompt.items()
        }
        
    def analysis_node(self):
        """分析工作流节点关系"""
        self.input_nodes_ids.clear()
        self.output_nodes_ids.clear()
        self.crypto_nodes_ids.clear()

        def find_input_nodes(node_id, visited=None):
            if visited is None:
                visited = set()
            if node_id in visited:
                return
            visited.add(node_id)
            self.input_nodes_ids.add(node_id)
            node = self.workflow_nodes_dict.get(node_id)
            if not node:
                return
            for input_node in node.get("inputs", []):
                input_link = input_node.get("link")
                if input_link is not None and input_link in self.link_owner_map:
                    owner_id = self.link_owner_map[input_link]["owner_id"]
                    find_input_nodes(owner_id, visited)

        for input_node in self.workflow_nodes_dict[self.save_crypto_node_id].get(
            "inputs", []
        ):
            if input_node["name"] and input_node["name"].startswith("input_anything"):
                input_link = input_node["link"]
                if input_link is not None and input_link in self.link_owner_map:
                    owner_id = self.link_owner_map[input_link]["owner_id"]
                    find_input_nodes(owner_id)

        def find_output_nodes(node_id, visited=None):
            if visited is None:
                visited = set()
            if node_id in visited:
                return
            visited.add(node_id)
            self.output_nodes_ids.add(node_id)
            node = self.workflow_nodes_dict.get(node_id)
            if not node:
                return
            for output in node.get("outputs", []):
                if not output or not output.get("links"):
                    continue
                for link in output.get("links", []):
                    if not link:
                        continue
                    if link is not None:
                        for workflow_link in self.workflow.get("links", []):
                            if workflow_link[0] == link:
                                target_node_id = workflow_link[3]
                                find_output_nodes(target_node_id, visited)

        output_links = set()
        for output_node in self.workflow_nodes_dict[self.crypto_bridge_node_id].get(
            "outputs", []
        ):
            _links = output_node["links"]
            output_links.update(_links)
        for link in self.workflow.get("links", []):
            if len(link) > 3 and link[0] in output_links:
                find_output_nodes(link[3])
        self.crypto_nodes_ids = (
            self.workflow_nodes_dict.keys()
            - self.input_nodes_ids
            - self.output_nodes_ids
        )
        self.crypto_nodes_ids = self.crypto_nodes_ids - {
            self.save_crypto_node_id,
            self.crypto_bridge_node_id,
        }
        
        return True
    
    def calculate_crypto_result(self, crypto_file_name=None):
        """计算加密结果"""
        self.crypto_result = {"prompt": {}, "workflow": {}, "outputs": []}
        for node_id in self.crypto_nodes_ids:
            if node_id in self.node_prompt_map:
                self.crypto_result["prompt"][node_id] = self.node_prompt_map[node_id]
            if node_id in self.workflow_nodes_dict:
                self.crypto_result["workflow"][node_id] = self.workflow_nodes_dict[
                    node_id
                ]
        crypto_bridge_node = self.node_prompt_map[self.crypto_bridge_node_id]
        for input_name, input_value in crypto_bridge_node.get("inputs", {}).items():
            if isinstance(input_value, list) and len(input_value) == 2:
                self.crypto_result["outputs"] = input_value[0], input_value[1]
                
        if crypto_file_name:
            json_result = json.dumps(self.crypto_result, indent=4, ensure_ascii=False)
            save_dir = folder_paths.temp_directory
            os.makedirs(save_dir, exist_ok=True)
            with open(os.path.join(save_dir, crypto_file_name), "w", encoding="utf-8") as f:
                f.write(json_result)
            return save_dir
        
        return self.crypto_result
    
    def output_workflow_simple_shell(self, output_workflow_name):
        """生成简化的工作流"""
        simplify_workflow = copy.deepcopy(self.workflow)
        save_crypto_node = None
        crypto_bridge_node = None
        for node in simplify_workflow["nodes"]:
            if node["id"] == self.save_crypto_node_id:
                save_crypto_node = node
            if node["id"] == self.crypto_bridge_node_id:
                crypto_bridge_node = node
        except_nodes_ids = self.crypto_nodes_ids.copy()
        except_nodes_ids.add(self.crypto_bridge_node_id)
        simplify_workflow["nodes"] = [
            node
            for node in simplify_workflow["nodes"]
            if int(node["id"]) not in except_nodes_ids
        ]
        if save_crypto_node is None:
            raise ValueError("ChenYuSaveLocalCryptoNode not found in workflow")
        if crypto_bridge_node is None:
            raise ValueError("ChenYuLocalCryptoBridgeNode not found in workflow")
        save_crypto_node["type"] = "ChenYuLocalDecodeCryptoNode"
        save_crypto_node["widgets_values"] = (
            [save_crypto_node.get("widgets_values", [None])[0]]
            if "widgets_values" in save_crypto_node
            else [None]
        )
        save_crypto_node["widgets_values"].append("")
        save_crypto_node["widgets_values"].append(False)
        save_crypto_node["properties"] = {"Node name for S&R": "ChenYuLocalDecodeCryptoNode"}
        if "outputs" not in crypto_bridge_node:
            save_crypto_node["outputs"] = []
        else:
            save_crypto_node["outputs"] = copy.deepcopy(crypto_bridge_node["outputs"])
        output_nodes_ids = [int(node["id"]) for node in simplify_workflow["nodes"]]
        filtered_links = []
        for link in simplify_workflow["links"]:
            if len(link) < 5:
                continue
            if link[1] == self.crypto_bridge_node_id:
                link[1] = self.save_crypto_node_id
            if link[1] in output_nodes_ids and link[3] in output_nodes_ids:
                filtered_links.append(link)
            else:
                pass
        simplify_workflow["links"] = filtered_links
        simplify_workflow.pop("groups", None)
        save_dir = folder_paths.output_directory
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, output_workflow_name)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(simplify_workflow, f, ensure_ascii=False, indent=4)
        return save_dir
    
    def encrypt_workflow(self, password, crypto_nodes=None, output_node_id=None, output_link_idx=None):
        """加密工作流的特定部分"""
        # 如果没有提供加密节点，使用分析结果
        if crypto_nodes is None:
            crypto_nodes = self.crypto_nodes_ids
        
        # 如果没有提供输出信息，使用计算结果
        if output_node_id is None or output_link_idx is None:
            self.calculate_crypto_result()
            output_node_id, output_link_idx = self.crypto_result["outputs"]
        
        # 刷新加密结果
        self.calculate_crypto_result()
        
        # 将数据转换为JSON
        json_data = json.dumps(self.crypto_result, indent=4, ensure_ascii=False)
        
        # 创建临时文件
        temp_dir = folder_paths.temp_directory
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f"local_crypto_{self.template_id}.json")
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        
        # 压缩和加密
        encrypted_file_path = os.path.join(temp_dir, f"local_crypto_{self.template_id}.zip")
        
        try:
            with pyzipper.AESZipFile(
                encrypted_file_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zipf:
                if isinstance(password, str):
                    password = password.encode("utf-8")
                else:
                    raise ValueError("密码必须是字符串")
                zipf.setpassword(password)
                zipf.write(temp_file_path, f"crypto_{self.template_id}.json")
            
            # 读取加密后的数据
            with open(encrypted_file_path, "rb") as f:
                encrypted_data = f.read()
                
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(encrypted_file_path):
                os.remove(encrypted_file_path)
            
            return encrypted_data
        except Exception as e:
            print(f"加密工作流失败: {str(e)}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(encrypted_file_path):
                os.remove(encrypted_file_path)
            return None
    
    @staticmethod
    def decrypt_workflow(encrypted_data, password):
        """解密工作流数据"""
        try:
            # 创建BytesIO对象
            zip_data = BytesIO(encrypted_data)
            
            # 使用AESZipFile解密
            with pyzipper.AESZipFile(zip_data) as zip_ref:
                zip_ref.setpassword(password.encode("utf-8"))
                file_name = zip_ref.namelist()[0]
                workflow_content = zip_ref.read(file_name)
                
                # 解析JSON数据
                return json.loads(workflow_content.decode("utf-8"))
        except Exception as e:
            print(f"解密工作流失败: {str(e)}")
            return None 