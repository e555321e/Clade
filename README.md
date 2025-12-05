# 🦎 Clade - AI 演化沙盒  （中文名待定）

> **在这个游戏里，你是上帝。**
>
> 创造生命，释放天灾，然后看着它们努力活下去（或者灭绝）。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" />
  <img src="https://img.shields.io/badge/Node.js-18+-green?logo=nodedotjs" />
  <img src="https://img.shields.io/badge/AI-DeepSeek%20%7C%20GPT%20%7C%20Claude-purple" />
</p>



---

## 🎮 这是什么？

**Clade** 是一个 AI 驱动的生物演化模拟器。想象一下《孢子》遇上《环世界》，再加上一个会讲故事的 AI —— 就是这个感觉。

你可以：
- 🌍 **创造世界** - 一张由 128×40 个六边形组成的动态地图
- 🧬 **设计生命** - AI 会帮你生成独特的生物，有名字、有器官、有性格
- ☄️ **降下天灾** - 火山爆发、冰河期、陨石撞击...看谁能挺过去
- 📊 **见证演化** - 数百万年的进化在几分钟内上演，族谱树实时更新

每次游戏都是独一无二的故事。你的"三眼喷墨章鱼"可能会统治海洋，也可能被一群"光合作用甲壳蟹"取而代之，甚至还可能演化出……猫娘？

---

## 🚀 5 分钟上手

### 第一步：安装必备软件

> ⚠️ **重要提示**：本游戏需要同时安装 **Python** 和 **Node.js**，两者缺一不可！
> - **Python** 用于运行后端模拟引擎和 AI 服务
> - **Node.js** 用于运行前端界面

如果你还没有安装，请先下载安装：
注意！！目前只支持python3.12，请下载对应版本的python安装
| 软件 | 版本要求 | 下载链接 |
|------|---------|----------|
| **Python** | 3.12  | [👉 点击下载](https://www.python.org/downloads/) |
| **Node.js** | 18 或更高 | [👉 点击下载](https://nodejs.org/zh-cn) |

<details>
<summary>📖 安装小贴士（点击展开）</summary>

#### Windows 用户

**安装 Python：**
1. 点击上面的链接，下载3.12.9版本的 Python（如果已经安装新版本没事，启动脚本会自动识别3.12版本的Python）
2. 运行安装程序时，**一定要勾选 "Add Python to PATH"**（这很重要！）
3. 点击 "Install Now" 完成安装

**安装 Node.js：**
1. 点击上面的链接，下载 LTS（长期支持）版本
2. 一路点击 "Next" 完成安装即可

**验证安装：**
打开命令提示符（按 `Win+R`，输入 `cmd`，回车），输入：
```
python --version
node --version
```
如果都显示版本号，说明安装成功！

#### Mac 用户（未经测试）

推荐使用 Homebrew 安装：
```bash
brew install python@3.12 node
```

#### Linux 用户

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv nodejs npm

# Fedora
sudo dnf install python3.12 nodejs
```

</details>

### 第二步：下载游戏

**方式 A：直接下载（推荐新手）**
1. 点击页面右上角绿色的 `Code` 按钮
2. 选择 `Download ZIP`
3. 解压到你喜欢的位置

**方式 B：使用 Git**
```bash
git clone https://github.com/Pocketfans/Clade.git
cd Clade
```

### 第三步：启动游戏

#### 🪟 Windows 用户（超简单！）

双击 `start.bat`，就直接自动化安装完成了！

启动器会自动：
- ✅ 检查 Python 和 Node.js
- ✅ 安装所有依赖
- ✅ 启动后端和前端服务
- ✅ 打开浏览器

<details>
<summary>📖 一键脚本不工作？点击查看手动启动方法</summary>

如果双击 `start.bat` 或 `start.ps1` 没有反应，可以手动启动：

**第一步：启动后端**

打开 **PowerShell** 或 **命令提示符**，运行：

```powershell
# 进入项目目录（改成你自己的路径）
cd C:\你的路径\Clade

# 进入后端目录
cd backend

# 创建虚拟环境（只需第一次）
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1
# 如果是 CMD 命令提示符，用这个：
# .\venv\Scripts\activate.bat

# 安装依赖（只需第一次）
pip install -e ".[dev]"

# 启动后端服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8022
```

**第二步：启动前端**

**新开一个** PowerShell 或命令提示符窗口，运行：

```powershell
# 进入项目目录（改成你自己的路径）
cd C:\你的路径\Clade

# 进入前端目录
cd frontend

# 安装依赖（只需第一次）
npm install

# 启动前端服务
npm run dev
```

**第三步：访问游戏**

打开浏览器，访问：**http://localhost:5188**

> 💡 **提示**：
> - 两个窗口都要保持打开状态，关闭任意一个都会导致服务停止
> - 如果端口 8022 或 5188 被占用，可以在 `.env` 文件中修改

</details>

#### 🍎 Mac / 🐧 Linux 用户（未经测试）

打开终端，依次运行：

```bash
# 1. 启动后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8022 &

# 2. 启动前端（新开一个终端窗口）
cd frontend
npm install
npm run dev
```

然后打开浏览器访问：**http://localhost:5188**

---

## 🔑 配置 AI（必须！）

游戏需要 AI 服务来生成物种和叙事。别担心，设置很简单：

> ⚠️ **重要提示**：本游戏需要两种 AI 模型：
> - **Chat 模型**（对话模型）：用于生成物种描述、叙事文本等
> - **Embedding 模型**（嵌入模型）：用于物种特征向量化、语义分析等
> 
> 请确保你选择的 AI 服务商同时支持这两种模型！

### 首选推荐：硅基流动

|--------|------|----------|
| **硅基流动** |  **强烈推荐！** 同时提供 Chat 模型和 Embedding 模型| [👉 注册](https://cloud.siliconflow.cn/) |

> 💡 **为什么推荐硅基流动？**
> - ✅ 同时支持 Chat 和 Embedding 两种模型类型（本游戏必需）且提供免费的Embedding模型
> - ✅ 提供多种模型选择（DeepSeek、Qwen、GLM 等）
> - ✅ 国内访问稳定，无需科学上网

### 其他选择（国内用户友好）

| 服务商 | 特点 | 注册链接 |
|--------|------|----------|
| **DeepSeek** | 便宜好用，中文优秀（需搭配其他 Embedding 服务） | [👉 注册](https://platform.deepseek.com/) |
| **火山引擎** | 豆包大模型 | [👉 注册](https://www.volcengine.com/product/doubao) |

### 国际用户

| 服务商 | 特点 | 注册链接 |
|--------|------|----------|
| **OpenAI** | GPT-5 强大但贵 | [👉 注册](https://platform.openai.com/) |
| **Google AI** | Gemini 免费额度多 | [👉 注册](https://aistudio.google.com/) |
| **Anthropic** | Claude 思维清晰 | [👉 注册](https://console.anthropic.com/) |

### 配置步骤

1. 游戏启动后，点击右上角的 **⚙️ 设置**
2. 找到 **"AI 服务"** 部分
3. 选择你注册的服务商
4. 填入 API Key
5. 点击 **"测试连接"** 确认可用
6. 保存！

> 💡 **小贴士**：DeepSeek v3.2 是性价比之王，前期一回合甚至不到1分钱，够玩很久了！

---

## 🎯 游戏玩法

### 🌟 核心循环
在这个世界里，时间以"回合"为单位流逝。每一回合代表着数千年甚至上百万年的岁月。

1. **环境变迁** 🌧️
   - 海平面升降、气温波动、降水变化
   - 板块漂移（可选）：大陆的分裂与合并会彻底改变生物的迁徙路线
   
2. **生存竞争** 🦁
   - **食物网**：捕食者追逐猎物，草食动物寻找植被。生态平衡一旦打破，可能导致连锁灭绝。
   - **迁徙**：动物会为了生存寻找更适宜的栖息地，或者为了躲避灾难而长途跋涉。
   - **死亡**：饥饿、寒冷、酷热、被捕食...只有最适者才能生存。

3. **演化与变异** 🧬
   - **基因漂移**：种群的基因库会随着时间随机改变。
   - **适应性进化**：长毛象在寒冷中演化出厚皮毛，沙漠蜥蜴学会保存水分。
   - **物种分化**：当一群生物被地理隔离太久，它们会分化成全新的物种。
   - **杂交**：相近的物种相遇时可能产生后代，诞生奇特的混种生物。

4. **AI 叙事** 🤖
   - 这一切不仅仅是枯燥的数据。AI 会观察你的世界，为新物种命名，描述它们的外貌特征，记录它们的兴衰历史。

### 🎮 上帝的工具箱

作为观察者和操控者，你拥有以下权能：

| 功能 | 描述 |
|------|------|
| **推进时间** | 点击"下一回合"，看着沧海桑田在指尖流转。 |
| **降下天灾** | 觉得世界太安逸了？试试 **陨石撞击**、**冰河世纪** 或 **火山爆发**。 |
| **物种透视** | 点击地图上的任意物种，查看它的详细档案：从骨骼结构到生活习性。 |
| **族谱追踪** | 打开全景族谱树，追溯任何一个物种的祖先，看清演化的脉络。 |
| **生态分析** | 使用向量分析工具，查看物种间的竞争关系和生态位分布。 |
| **平行世界** | 利用存档功能，在关键节点分叉出不同的时间线，探索"如果那时..."的可能性。 |

### ⚙️ 进阶设置

在"设置"面板中，你可以微调世界的法则：
- **板块构造系统**：开启后，大陆会真实地漂移、碰撞、造山。
- **生态参数**：调整基础代谢率、变异概率、环境承载力等核心参数。
- **AI 模型**：切换不同的 AI 模型来获得不同风格的物种描述（支持 DeepSeek, Claude, GPT 等）。

---

## ❓ 常见问题

<details>
<summary><b>Q: 双击 start.bat 没反应？</b></summary>

1. 确保 Python 和 Node.js 已正确安装
2. 右键 `start.bat`，选择"以管理员身份运行"
3. 如果还不行，手动运行命令（见上方手动启动说明）

</details>

<details>
<summary><b>Q: 报错说端口被占用？</b></summary>

可能是上次没有正确关闭。双击 `stop.bat` 关闭所有服务，然后重新启动。

或者修改端口：
- 后端：编辑项目根目录的 `.env` 文件，修改 `BACKEND_PORT=8022`
- 前端：在 `frontend/vite.config.ts` 中修改端口

</details>

<details>
<summary><b>Q: AI 返回空白/报错？</b></summary>

1. 检查 API Key 是否正确
2. 检查账户余额是否充足
3. 尝试切换其他模型或服务商

</details>

<details>
<summary><b>Q: 如何重置世界？</b></summary>

进入游戏后，点击 **设置 → 开发者工具 → 重置世界**。

或者直接删除 `data/` 文件夹下的所有内容（保留 `settings.example.json`）。

</details>

<details>
<summary><b>Q: 可以离线玩吗？</b></summary>

游戏本身可以离线运行，但物种生成和叙事需要 AI 服务。没有 AI 的话，演化会使用简化规则，但会少很多乐趣。

</details>

---

## 📁 文件说明

```
Clade/
├── start.bat          # 🚀 Windows 一键启动
├── stop.bat           # 🛑 关闭所有服务
├── backend/           # 后端引擎（Python）
├── frontend/          # 前端界面（React）
├── data/              # 存档和配置（游戏生成）
│   └── settings.example.json  # 配置模板
└── docs/              # 开发文档
```

---

## 🛠️ 开发者信息

想深入了解技术细节？查看：

- [开发文档](DEV_DOC.md) - 架构设计与核心算法
- [API 指南](API_GUIDE.md) - 接口文档
- [模块文档](docs/api-guides/README.md) - 各模块详细说明

### 技术栈

- **后端**：Python 3.11 + FastAPI + SQLModel + NumPy
- **前端**：React + TypeScript + Vite + D3.js
- **AI**：支持 OpenAI API 兼容的任何服务


---

## ⚙️ 张量配置（前端可调）

- 读取当前配置：`GET /tensor/config`，返回 `{ path, config }`，`config` 结构同 `UIConfig.tensor`/`tensor_balance.yaml`。
- 更新配置：`PUT /tensor/config`，支持部分字段（深度合并），示例：
  ```json
  {
    "use_tensor_mortality": true,
    "balance": {
      "temp_optimal": 22,
      "birth_rate_growth_per_100_turns": 0.02
    },
    "energy_costs": { "运动能力": 1.6 }
  }
  ```
  更新后会写回 `tensor_balance.yaml` 并热加载引擎，张量开关同步。
- 前端表单字段（参考 `UIConfig.tensor` 描述）：
  - 开关：张量死亡率/分化检测/自动代价
  - 温度：最适/容忍度、每100回合漂移/变化、温度通道索引
  - 种群动态：扩散率与增长、出生率与增长、竞争强度与衰减、承载力乘数、植被敏感度
  - 分化检测：分歧阈值、方差归一化
  - 适应度：最低适应度
  - 代价：tradeoff_ratio、energy_costs、competition_map、default_penalty_pool

---

## 👋 写在后面

大家好，我是 **幻想口袋**

📺 **B站主页**：[https://space.bilibili.com/2965629](https://space.bilibili.com/2965629)

说实话，这个项目是我面向AI编程的，虽然整体架构基本上都是我自己设计的，但代码的大部分都是 AI 辅助生成的。

所以，这个项目肯定有很多问题和 bug。 

我没法保证代码有多优雅，架构有多合理。但我希望大家能在这个项目中体会到物种演化的神奇和乐趣，这也是我的初衷。

**如果你也喜欢这个项目，非常欢迎你来帮忙！** 不管是：
- 🔧 修复一个 bug
- ✨ 优化一段代码
- 📝 完善一处文档
- 💡 提出一个建议

对我来说都是莫大的帮助。这个项目是开源的，属于每一个愿意参与的人。
---

## 🤝 参与贡献

因为这是一个 AI 辅助开发的项目，代码中难免存在各种问题：
- 可能有些地方逻辑不够严谨
- 可能有些代码风格不够统一
- 可能有些功能实现得不够优雅

**但这正是开源的意义所在** —— 集众人之力，让它变得更好。

如果你愿意帮忙，可以：
1. **提 Issue**：发现 bug 或有建议，直接开 Issue 告诉我
2. **提 PR**：如果你修复了问题或添加了功能，欢迎提交 PR
3. **讨论**：对项目有任何想法，可以在 Discussions 里聊

不管贡献大小，我都非常感谢！🙏

---

## 📬 联系我

- **B站**：[幻想口袋](https://space.bilibili.com/2965629) - 会发布项目相关视频和更新
- **GitHub Issues**：有问题直接提 Issue，我会尽量回复

---

## 📄 开源协议

**AGPL-3.0 (后端) + MPL-2.0 (前端)**

本项目采用双重许可证模式：

| 组件 | 许可证 | 说明 |
|------|--------|------|
| `backend/` | AGPL-3.0 | 后端核心代码 |
| `frontend/` | MPL-2.0 | 前端界面代码 |
| `docs/`, `*.md` | CC-BY-4.0 | 文档 |
| `data/`, `*.json`, `*.yaml` | MIT | 配置与数据 |

✅ **你可以**：
- 自由使用、学习、修改代码
- 在商业项目中使用（需遵守相应许可证条款）
- 基于此项目创建衍生作品
- 贡献代码回馈社区
- 将前端组件嵌入其他项目（遵守 MPL-2.0）

⚠️ **使用后端代码时 (AGPL-3.0)**：
- 修改后的版本必须以 AGPL-3.0 开源
- 通过网络提供服务时，必须提供源代码

⚠️ **使用前端代码时 (MPL-2.0)**：
- 修改的 MPL 文件必须开源
- 新增的文件可以使用其他许可证

详见 [LICENSE](LICENSE) 文件



---

<p align="center">
  <b>让生命自由演化，让 AI 讲述故事。</b>
  <br><br>
  这是一个用爱发电的项目，如果觉得有趣，请给个 ⭐ Star 支持一下！
</p>
