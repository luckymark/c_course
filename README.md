# C语言学习笔记本

> **开始前请注意：在线输入限制**
> 当前在线环境中的 `scanf`、`getchar`、`fgets(..., stdin)` 无法交互读取键盘输入。在线实验请修改变量的初值，或使用 `sscanf` 从字符串读取；键盘输入练习请在本地 GCC / Clang 中运行完整 C 程序。

参考书目：电子科技大学出版社《C与C++程序设计》，戴波主编；陈文宇、丘志杰、卢光辉副主编。

本项目使用 Jupyter Notebook 提供可运行的 C 语言课堂实验，章节编排与教材对应：

1. C语言程序设计概述
2. 基本数据类型及运算
3. 控制语句
4. 数组与结构
5. 指针
6. 函数

每章包含学习目标、“预测—运行—修改—解释”实验、4 道分层练习和一个完整的本地 C17 程序。练习提示与参考思路默认折叠；先在新代码单元中尝试，再展开核对。

贯穿案例逐章发展为成绩统计程序：报告输出 → 成绩计算 → 合法性与及格判断 → 结构体数组统计 → 动态分配成绩空间 → 通过只读参数与返回值组织统计函数。每章都可独立重启内核运行，不依赖上一章的变量状态。

## 在线学习

打开 [课程网站](https://luckymark.github.io/c_course)，选择章节笔记本，使用 **C17** 内核，从上到下运行单元。首次启动需要下载 WebAssembly 内核，请等待内核就绪。

- `Shift+Enter` 运行当前单元。
- 修改 `{ ... }` 中的局部变量后，可以重复运行该单元。
- 修改函数、结构体或顶层变量定义后，使用 **Kernel → Restart Kernel and Run All Cells**，避免旧定义影响结果。
- 使用下载功能保存自己的 Notebook；浏览器中的修改不会提交到此仓库。

Notebook 支持直接执行语句，这是交互环境的功能。普通 `.c` 文件仍需要头文件和 `main` 函数。第 1 章分别提供了完整程序和在线实验；不要把所有单元直接拼接为 `.c` 文件，也不要在 Notebook 中手动调用 `main()`。

## 标准输入的限制

当前固定的浏览器版 xeus-cpp 0.10.0 中，C17 内核的行为如下：

| 操作 | 浏览器实测行为 |
| --- | --- |
| `printf` | 正常输出 |
| `sscanf` | 可以从字符串读取数据 |
| `scanf` | 返回 EOF，不弹出键盘输入框 |
| `getchar` | 返回 EOF |
| `fgets(..., stdin)` | 返回 NULL |

这些是浏览器内核的限制，不是 C 语言的规则。在线实验使用明确赋值或 `sscanf`；第 2 章保留了检查 `scanf` 返回值的完整本地程序。`std::cin` 属于 C++，不能用于本课程的 C17 内核。

键盘输入练习请将完整程序保存为 `.c` 文件，使用本地 GCC 或 Clang 编译，例如：

```bash
cc -std=c17 -Wall -Wextra -Wpedantic hello.c -o hello
./hello
```

本地原生 Jupyter 内核与浏览器内核是不同的运行环境，上表不用于判断原生内核的支持情况。

## 构建与验证

构建环境使用 Python 3.14（允许更新补丁版本），固定 JupyterLite 0.8.3、jupyterlite-xeus 5.1.0；WebAssembly 环境固定为 xeus-cpp 0.10.0，使用 emscripten-forge-4x 软件源。版本声明分别位于 `build-environment.yml` 和 `environment.yml`。这两份文件固定核心依赖，不是全部间接依赖的锁文件。

安装 [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html) 后，在仓库根目录执行：

```bash
micromamba create -n c-course-build -f build-environment.yml -y
micromamba run -n c-course-build jupyter lite build --contents content --output-dir dist
micromamba run -n c-course-build python -m http.server 8765 --bind 127.0.0.1 --directory dist
```

打开 <http://127.0.0.1:8765/lab/>。`environment.yml` 用于构建浏览器内核，不能直接作为本机原生 C 内核的安装环境。

[浏览器检查脚本](tests/browser_smoke.py) 的模块说明包含测试安装和运行命令。它在全新浏览器配置中检查 C17 内核版本、函数、单元重复执行、内核重启、输入限制，并逐章执行站点中的所有非空代码单元。测试只在自己的页面响应中启用应用调试入口，不修改发布站点。

关键实验的预期输出保存在对应单元的元数据中，由浏览器检查直接核对。[本地程序检查脚本](tests/native_examples.py) 从各章提取完整 C 程序，以严格警告选项编译，并验证正常输入、边界和错误输入的输出与退出码。完整程序只在 Notebook 中维护。

GitHub Actions 在构建及 Chromium 检查成功后才发布 GitHub Pages。
