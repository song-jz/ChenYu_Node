# custom_nodes/my_custom_node/my_node.py
from nodes import MAX_RESOLUTION

class ChenyuEncryptionNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": ("IMAGE",)}}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "Custom Nodes"  # 分类名影响在UI中的显示位置

    def process(self, image):
        return (image, )

NODE_CLASS_MAPPINGS = {"ChenyuEncryptionNode": ChenyuEncryptionNode}
NODE_DISPLAY_NAME_MAPPINGS = {"ChenyuEncryptionNode": "✨ ChenyuEncryptionNode"}