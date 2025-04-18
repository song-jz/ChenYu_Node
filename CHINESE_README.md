[Read English](ENGLISH_README.md)

# 晨羽节点加密: ComfyUI压缩加密节点

## 简介
晨羽节点加密是一个小巧的ComfyUI开源节点，它的作用在于简化工作流，同时给工作流提供加密保护。

![image](docs/image1.png)

## 应用场景
- 流程简化：可以大幅度简化工作流。
- 加密授权：可以保护工作流里的一些核心思路。

## 快速开始
你可以在这里看到一个简单的 [Workflow Demo](demo/original.json)

### 安装和使用步骤
1. **安装节点**
   - 打开 ComfyUI\custom_Nodes\ 目录，克隆仓库到本地
   - 或在 ComfyUI-Manager 中安装 ComfyUI Compression and Encryption Node 节点

2. **启动和配置**
   - 启动 ComfyUI
   - 在菜单"高级"（advance）中找到 晨羽节点加密 目录

3. **🔐使用方法**
   - 加密组件和加密结束桥接一头一尾，控制工作流的加密区间
   - 随机种子会在服务端生成随机数，用于修补工作流封装后随机数不起效的情况


> ⚠️ 解密组件无需手动添加 - 加密后系统会在output文件夹自动生成包含解密组件的工作流
> 
> ⚠️ 加密时会自动生成10组序列号，用户首次使用时会与硬件信息绑定，后续使用时会验证序列号与硬件信息的一致性

  

## 贡献指南
欢迎对晨羽节点加密项目做出贡献！你可以通过提交Pull Request或开设Issue来提出新功能建议或报告问题。

## 许可证
本项目遵循MIT许可证。有关详细信息，请参阅LICENSE文件。

## 联系方式
Email：<hzxhzx321@gmail.com>

![image](docs/wechat.jpg)

---
晨羽节点加密 © 2024. All Rights Reserved.
