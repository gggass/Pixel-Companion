# Makefile for Pixel-Companion Hook Core
# 仅支持 Windows (MSVC/MinGW) 编译

# 默认目标：Windows MSVC 编译
all: windows_msvc

# Windows MSVC 编译配置
MSVC_CXX = cl.exe
MSVC_LIBS = user32.lib gdi32.lib
MSVC_FLAGS = /EHsc /O2
MSVC_TARGET = hook_core.exe

windows_msvc: $(MSVC_TARGET)
	$(MSVC_CXX) $(MSVC_FLAGS) hook_core.cpp /link $(MSVC_LIBS) /out:$(MSVC_TARGET)

# Windows MinGW 编译配置
MINGW_CXX = g++
MINGW_LIBS = -luser32 -lgdi32
MINGW_FLAGS = -O2 -std=c++17
MINGW_TARGET = hook_core.exe

windows_mingw: $(MINGW_TARGET)
	$(MINGW_CXX) $(MINGW_FLAGS) hook_core.cpp -o $(MINGW_TARGET) $(MINGW_LIBS)

# 清理目标
clean:
	@echo "清理编译文件..."
	-del $(MSVC_TARGET) 2>NUL || true
	-rm $(MINGW_TARGET) 2>NUL || true

.PHONY: all windows_msvc windows_mingw clean
