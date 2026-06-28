/*
 * Pixel-Companion Hook Core
 * Windows 平台底层按键与鼠标钩子核心。
 * 负责捕获全局键盘输入和鼠标事件，并通过标准输出发送 JSON 数据。
 */

#include <iostream>
#include <windows.h>
#include <string>
#include <vector>
#include <sstream>
#include <iomanip>
#include <thread>
#include <chrono>

// 全局钩子句柄
HHOOK keyboardHook = NULL;
HHOOK mouseHook = NULL;

// 辅助函数：将虚拟键码转换为字符串
std::string GetKeyName(DWORD vkCode) {
    char buffer[256];
    // MapVirtualKeyEx 无法直接获取所有键名，这里做简化处理
    // 实际应用中需要更复杂的映射表
    switch (vkCode) {
        case VK_LBUTTON: return "Mouse Left";
        case VK_RBUTTON: return "Mouse Right";
        case VK_MBUTTON: return "Mouse Middle";
        case VK_XBUTTON1: return "Mouse X1";
        case VK_XBUTTON2: return "Mouse X2";
        case VK_BACK: return "Backspace";
        case VK_TAB: return "Tab";
        case VK_RETURN: return "Enter";
        case VK_SHIFT: return "Shift";
        case VK_CONTROL: return "Ctrl";
        case VK_MENU: return "Alt";
        case VK_PAUSE: return "Pause";
        case VK_CAPITAL: return "Caps Lock";
        case VK_ESCAPE: return "Esc";
        case VK_SPACE: return "Space";
        case VK_PRIOR: return "Page Up";
        case VK_NEXT: return "Page Down";
        case VK_END: return "End";
        case VK_HOME: return "Home";
        case VK_LEFT: return "Left Arrow";
        case VK_UP: return "Up Arrow";
        case VK_RIGHT: return "Right Arrow";
        case VK_DOWN: return "Down Arrow";
        case VK_SELECT: return "Select";
        case VK_PRINT: return "Print";
        case VK_EXECUTE: return "Execute";
        case VK_SNAPSHOT: return "Print Screen";
        case VK_INSERT: return "Insert";
        case VK_DELETE: return "Delete";
        case VK_HELP: return "Help";
        case VK_LWIN: return "Left Win";
        case VK_RWIN: return "Right Win";
        case VK_APPS: return "Apps";
        case VK_NUMPAD0: return "Num 0";
        case VK_NUMPAD1: return "Num 1";
        case VK_NUMPAD2: return "Num 2";
        case VK_NUMPAD3: return "Num 3";
        case VK_NUMPAD4: return "Num 4";
        case VK_NUMPAD5: return "Num 5";
        case VK_NUMPAD6: return "Num 6";
        case VK_NUMPAD7: return "Num 7";
        case VK_NUMPAD8: return "Num 8";
        case VK_NUMPAD9: return "Num 9";
        case VK_MULTIPLY: return "Num *";
        case VK_ADD: return "Num +";
        case VK_SEPARATOR: return "Num Separator";
        case VK_SUBTRACT: return "Num -";
        case VK_DECIMAL: return "Num .";
        case VK_DIVIDE: return "Num /";
        case VK_F1: return "F1";
        case VK_F2: return "F2";
        case VK_F3: return "F3";
        case VK_F4: return "F4";
        case VK_F5: return "F5";
        case VK_F6: return "F6";
        case VK_F7: return "F7";
        case VK_F8: return "F8";
        case VK_F9: return "F9";
        case VK_F10: return "F10";
        case VK_F11: return "F11";
        case VK_F12: return "F12";
        case VK_NUMLOCK: return "Num Lock";
        case VK_SCROLL: return "Scroll Lock";
        case VK_LSHIFT: return "Left Shift";
        case VK_RSHIFT: return "Right Shift";
        case VK_LCONTROL: return "Left Ctrl";
        case VK_RCONTROL: return "Right Ctrl";
        case VK_LMENU: return "Left Alt";
        case VK_RMENU: return "Right Alt";
        case VK_OEM_1: return ";:";
        case VK_OEM_PLUS: return "+=";
        case VK_OEM_COMMA: return ",<";
        case VK_OEM_MINUS: return "-_";
        case VK_OEM_PERIOD: return ".>";
        case VK_OEM_2: return "/?";
        case VK_OEM_3: return "`~";
        case VK_OEM_4: return "[{";
        case VK_OEM_5: return "\\|";
        case VK_OEM_6: return "]}";
        case VK_OEM_7: return "'\"";
        case VK_OEM_8: return "!~";
        case VK_OEM_102: return "<>";
        default: {
            // 尝试获取字符
            BYTE keyboard_state[256];
            GetKeyboardState(keyboard_state);
            WCHAR unicode_char[2];
            int result = ToUnicode(vkCode, MapVirtualKey(vkCode, MAPVK_VK_TO_VSC), keyboard_state, unicode_char, 1, 0);
            if (result > 0) {
                // 将宽字符转换为多字节字符
                WideCharToMultiByte(CP_ACP, 0, unicode_char, 1, buffer, sizeof(buffer), NULL, NULL);
                return buffer;
            }
            // 如果无法转换为字符，则返回虚拟键码的十六进制表示
            std::stringstream ss;
            ss << 
0x" << std::hex << vkCode;
            return ss.str();
        }
    }
}

// 键盘钩子回调函数
LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        KBDLLHOOKSTRUCT* pKBDLLHookStruct = (KBDLLHOOKSTRUCT*)lParam;
        if (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN) {
            // 按键按下事件
            std::cout << "{\"event_type\": \"key_down\", \"key\": \"" << GetKeyName(pKBDLLHookStruct->vkCode) << "\", \"vk_code\": " << pKBDLLHookStruct->vkCode << "}" << std::endl;
        } else if (wParam == WM_KEYUP || wParam == WM_SYSKEYUP) {
            // 按键抬起事件
            // std::cout << "{\"event_type\": \"key_up\", \"key\": \"" << GetKeyName(pKBDLLHookStruct->vkCode) << "\", \"vk_code\": " << pKBDLLHookStruct->vkCode << "}" << std::endl;
        }
    }
    return CallNextHookEx(keyboardHook, nCode, wParam, lParam);
}

// 鼠标钩子回调函数
LRESULT CALLBACK LowLevelMouseProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        MSLLHOOKSTRUCT* pMSLLHookStruct = (MSLLHOOKSTRUCT*)lParam;
        std::string event_type;
        switch (wParam) {
            case WM_LBUTTONDOWN: event_type = "mouse_left_down"; break;
            case WM_LBUTTONUP: event_type = "mouse_left_up"; break;
            case WM_RBUTTONDOWN: event_type = "mouse_right_down"; break;
            case WM_RBUTTONUP: event_type = "mouse_right_up"; break;
            case WM_MBUTTONDOWN: event_type = "mouse_middle_down"; break;
            case WM_MBUTTONUP: event_type = "mouse_middle_up"; break;
            case WM_MOUSEMOVE: event_type = "mouse_move"; break;
            case WM_MOUSEWHEEL: event_type = "mouse_wheel"; break;
            default: event_type = "mouse_event"; break;
        }
        
        // 仅在鼠标移动或点击时输出，避免过多数据
        if (wParam == WM_MOUSEMOVE || wParam == WM_LBUTTONDOWN || wParam == WM_RBUTTONDOWN || wParam == WM_MBUTTONDOWN) {
            std::cout << "{\"event_type\": \"" << event_type << "\", \"x\": " << pMSLLHookStruct->pt.x << ", \"y\": " << pMSLLHookStruct->pt.y << "}" << std::endl;
        }
    }
    return CallNextHookEx(mouseHook, nCode, wParam, lParam);
}

// 消息循环函数
void MessageLoop() {
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
}

int main() {
    // 预热输出，确保 Python 端能正确解析初始 JSON
    std::cout << "{\"status\": \"Hook Core Initializing...\"}" << std::endl;

    // 设置键盘钩子
    keyboardHook = SetWindowsHookEx(WH_KEYBOARD_LL, LowLevelKeyboardProc, GetModuleHandle(NULL), 0);
    if (!keyboardHook) {
        std::cerr << "Failed to install keyboard hook! Error: " << GetLastError() << std::endl;
        return 1;
    }

    // 设置鼠标钩子
    mouseHook = SetWindowsHookEx(WH_MOUSE_LL, LowLevelMouseProc, GetModuleHandle(NULL), 0);
    if (!mouseHook) {
        std::cerr << "Failed to install mouse hook! Error: " << GetLastError() << std::endl;
        UnhookWindowsHookEx(keyboardHook); // 卸载已安装的键盘钩子
        return 1;
    }

    std::cout << "{\"status\": \"Hooks installed successfully.\"}" << std::endl;

    // 运行消息循环
    MessageLoop();

    // 卸载钩子
    UnhookWindowsHookEx(keyboardHook);
    UnhookWindowsHookEx(mouseHook);

    return 0;
}
