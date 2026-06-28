# 🐾 Pixel-Companion: 桌面像素伙伴

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![C++](https://img.shields.io/badge/Language-C++17-blue.svg)](https://isocpp.org/)
[![Python](https://img.shields.io/badge/Language-Python3.12+-blue.svg)](https://www.python.org/)

**Pixel-Companion** 是一款充满趣味的桌面互动宠物应用。它不仅能在你的桌面上陪伴你，还能实时可视化你的键盘输入，并为鼠标增添炫酷的粒子特效，让你的桌面操作变得生动有趣。

---

## ✨ 核心特性

- **🐾 桌面宠物**：一个可爱的像素风格宠物，始终悬浮在桌面右下角，不干扰你的工作。
- **⌨️ 按键可视化**：当你敲击键盘时，宠物上方会以对话框的形式实时显示你按下的键，支持特殊按键的识别。
- **✨ 鼠标粒子特效**：鼠标移动时会产生多彩的粒子拖尾效果，点击宠物可切换或配置特效。
- **🚀 高性能**：C++ 核心使用 Windows 底层钩子（Hooks）捕获键盘和鼠标事件，确保极低的资源占用和流畅的体验。
- **🎨 透明窗口**：基于 Python (PyQt) 实现，宠物和特效以透明窗口形式呈现，完美融入桌面。

## 🛠️ 工作原理

Pixel-Companion 采用 **C++ 核心 + Python GUI** 的混合架构：

1.  **Hook Core (C++)**：
    *   部署在 Windows 系统上，利用 `SetWindowsHookEx` API 设置全局低级键盘钩子 (`WH_KEYBOARD_LL`) 和鼠标钩子 (`WH_MOUSE_LL`)。
    *   实时捕获所有键盘按键事件和鼠标移动/点击事件。
    *   将捕获到的事件信息（如按键名称、鼠标坐标、事件类型）格式化为 JSON 字符串，并通过标准输出 (stdout) 发送。

2.  **Pixel Companion GUI (Python)**：
    *   使用 PyQt5 框架创建一个无边框、背景透明的窗口。
    *   启动 C++ Hook Core 进程，并通过管道实时读取其标准输出的 JSON 数据。
    *   根据接收到的键盘事件，在宠物上方动态显示按键信息。
    *   根据接收到的鼠标事件，在鼠标当前位置生成并渲染粒子效果。
    *   提供简单的交互，例如点击宠物可以切换鼠标特效的开关。

## 🚀 快速开始

### 环境要求
- **操作系统**：Windows 10/11 (本项目专为 Windows 设计)
- **C++ 编译器**：Visual Studio (MSVC) 或 MinGW
- **Python 3.12+**

### 部署与运行

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/gggass/Pixel-Companion.git
    cd Pixel-Companion
    ```

2.  **编译 C++ Hook Core**:
    - **Windows (MSVC)**: `make windows_msvc` (或手动使用 `cl.exe` 编译)
    - **Windows (MinGW)**: `make windows_mingw` (或手动使用 `g++` 编译)
    *编译成功后，会生成 `hook_core.exe` 可执行文件。*

3.  **安装 Python 依赖**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **准备宠物图片**:
    *   在项目根目录下创建 `assets` 文件夹。
    *   将你的像素宠物图片（例如 `pixel_pet.png`）放入 `assets` 文件夹中。
    *   如果 `assets/pixel_pet.png` 不存在，程序将自动创建一个红色的占位符方块。

5.  **运行 Pixel Companion**:
    ```bash
    python pixel_companion.py
    ```
    *宠物将出现在桌面右下角，并开始捕获按键和鼠标事件。*

## 📜 文件说明
- `hook_core.cpp`: Windows 底层按键与鼠标钩子 C++ 核心源码。
- `pixel_companion.py`: Python GUI 脚本，负责桌面宠物、按键可视化和鼠标特效的渲染。
- `Makefile`: 编译脚本，支持 Windows MSVC 和 MinGW 编译器。
- `requirements.txt`: Python 依赖列表。
- `README.md`: 项目介绍与使用指南。
- `assets/`: 存放宠物图片等资源。

## 🤝 贡献指南
欢迎提交 Issue 或 Pull Request 来增加更多宠物、特效或优化功能。

## 📄 开源协议
本项目采用 MIT 协议开源。

---
由 **gggass** 精心打造。
