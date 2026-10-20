# GitHub 首页是怎么做的

你看到的页面是 GitHub 渲染的 README，不需要部署网站。把根目录的 `README.md` 和引用的图片提交到仓库，GitHub 会显示项目介绍。

本项目已准备好首页：标题和徽章在顶部，下面是功能、实际界面截图、芯片范围、开始使用和验收说明。详细说明放在 `docs/USAGE.md`，首页通过相对链接连接它们。

## 常用写法

```markdown
# FlashDesk

单片机烧录工作台。

![Windows](https://img.shields.io/badge/platform-Windows_x64-175CD3?style=flat-square)

![程序界面](docs/images/workbench.png)

## 功能

- 按芯片显示配置
- 工程方案保存和分区重置

| 芯片系列 | 后端 |
|---|---|
| ESP32 | esptool |

[使用说明](docs/USAGE.md)
```

居中标题和并排徽章可使用少量 HTML：

```html
<h1 align="center">FlashDesk</h1>
<p align="center">单片机烧录工作台</p>
<p align="center">
  <img src="https://img.shields.io/badge/version-0.3.0-175CD3?style=flat-square" alt="Version 0.3.0">
  <img src="https://img.shields.io/badge/status-preview-D69E2E?style=flat-square" alt="Preview">
</p>
```

徽章是图片：静态徽章可以显示版本、平台、开发状态；Stars、Release、CI 等动态徽章需要真实仓库或任务作为数据源。本项目没有伪造这些指标，也没有在未选许可证时标成 MIT。

参考：[GitHub 官方 README 说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)、[Shields.io 静态徽章](https://shields.io/badges/static-badge)。

## 上传本项目

1. 在 GitHub 创建你自己的仓库，决定公开范围、仓库名和项目许可证。
2. 提交源码、测试、脚本、根目录文档、`docs/images/`、`docs/USAGE.md` 等文件。仓库根目录应直接包含 `README.md` 和 `flashdesk/`。GitHub Desktop 的 Create 可能按名称新建子目录；需要确认项目文件实际位于新仓库内，不能仅创建空仓库。
3. 使用 Git 时，项目的 `.gitignore` 会排除 `.venv/`、`build/`、`dist/` 和本机原始运行记录。浏览器手动上传不会使用这些忽略规则，需要自己排除它们。
4. 检查 GitHub 首页上的相对图片和文档链接。仓库有地址后，再加入真实的 Release 下载地址和动态徽章。
5. 可执行程序适合在 GitHub Releases 发布完整目录的 ZIP；不要只上传一个依赖文件不全的 EXE，也不要把开发虚拟环境当成源码提交。

## 给普通用户发布 Windows 程序

源码仓库没有 `dist/` 是正常的。源码更新通过 GitHub Desktop 的 Commit / Push 发布；可直接运行的程序通过 Releases 单独发布，二者分别更新。

1. 本机构建并完成测试后，把整个 `dist/FlashDesk/` 文件夹压缩成 `FlashDesk-v0.3.0-windows-x64.zip`，保留里面的 `_internal`、`examples`、`third-party`、文档等配套文件。
2. 打开 GitHub 仓库 → 右侧 **Releases** → **Create a new release**，创建对应版本标签，填写更新内容。
3. 将程序 ZIP 拖到附件区域，再发布 Release。GitHub 自动生成的 `Source code (zip)` / `Source code (tar.gz)` 仍是源码，不是程序。
4. 用户选择你上传的 Windows ZIP，解压运行 `FlashDesk.exe`。只想使用软件的人无需安装 Python；开发者克隆源码后通过 `启动工作台.cmd` 初始化依赖。

准备 Release 不需要取消 `.gitignore` 对 `dist/` 的忽略。修改过的启动脚本和 README 需要 Commit 并 Push，远端克隆者才能获得修复。

根目录 `THIRD_PARTY.md` 记录了第三方依赖许可。本项目自身的 LICENSE 尚未选定；发布前应选定与实际分发方式、GPL / LGPL 等依赖义务相容的许可并提供相应材料。这与首页排版是独立事项。

GitHub 会使用自己的样式与净化规则；README 不依赖自定义 JavaScript、样式表或页面服务。本地预览用于查看排版，最后仍以 GitHub 实际渲染为准。
