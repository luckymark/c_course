# C语言学习笔记本

参数书目：电子科技大学出版的教材《C与C++程序设计》 戴波 主编；陈文宇 丘志杰 卢光辉 副主编

本项目包含一系列 Jupyter Notebook，用于初学者学习 **C 语言** 基础知识与编程技巧。 

笔记本内容涵盖： （章节编排与《C与C++程序设计》一书相同）
- C语言程序设计概述 
- 基本数据类型及运算 
- 控制语句 
- 数组与结构
- 指针
- 函数


---

## 使用方法

1. 克隆或下载本仓库到本地； 
2. 打开 JupyterLab / JupyterLite，选择 **C/C++ Kernel**（ `xeus-cpp` ）。  xeus-cpp需自行安装，安装方法请参考：https://github.com/compiler-research/xeus-cpp
3. 运行笔记本中的代码单元，跟随注释学习和修改。  

或直接在 [JupyterLite 页面](https://luckymark.github.io/c_course) 上在线运行。

---

## 注意事项

- 当前所用的 **Jupyter Kernel** 并不完全支持标准 C 的所有输入输出函数。  
- 特别是 **`scanf`** 在交互式 Notebook 环境中不可用。  
  - 例如，以下代码在 Notebook 中无法运行：  
    ```c
    int a;
    scanf("%d", &a);
    ```
- 推荐使用 **C++ 风格的 `std::cin`** 替代输入：  
    ```cpp
    int a;
    std::cin >> a;
    ```
- 其余代码（如 `printf` 输出、指针、数组、结构体、函数等）均可正常使用。  

---

## 建议

- 初学者可以按章节顺序学习。  
- 笔记本内附有大量示例，建议边学边改，尝试不同的输入与输出。  
- 学习完成后，可以尝试将 Notebook 中的代码保存为 `.c` 文件，在本地 GCC 或 Clang 环境中编译运行，以获得完整的 C 语言体验。  

---

祝学习愉快 🚀  