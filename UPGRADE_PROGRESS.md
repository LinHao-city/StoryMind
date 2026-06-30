# OpenMontage 升级进度文档

> 目标：让 AI 能根据策划案自动生成高质量分镜方案，并保障人物和故事情节的前后一致性。

---

## 调研来源

| 项目 | Stars | 核心贡献 |
|------|-------|---------|
| [Toonflow](https://github.com/HBAI-Ltd/Toonflow-app) | 10,878 | 剧本→分镜→视频完整链路 |
| [Jellyfish](https://github.com/Forget-C/Jellyfish) | 4,666 | 结构化分镜+一致性管理 |
| [HunyuanVideo 1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) | 4,502 | LoRA 锁定角色外观 |
| [ControlNeXt](https://github.com/JIA-Lab-research/ControlNeXt) | 1,644 | ControlNet+LoRA 精确构图控制 |
| [Radial Attention](https://github.com/mit-han-lab/radial-attention) | 602 | 长视频跨场景时间一致性 |
| [InstantID](https://github.com/InstantX-Team/InstantID) | ~12k | 参考图锁定人脸跨镜头一致 |

---

## 升级架构总览

```
策划案 / 剧本
      ↓
┌─────────────────────────────────────────────┐
│  Phase 1：分镜智能规划层（已实施）               │
│  • StoryboardPlanner  — LLM 拆解镜头语言       │
│  • CharacterSheet     — 角色锚点登记            │
│  • CinematographyDirector skill — 导演知识库   │
└─────────────────────────────────────────────┘
      ↓  结构化分镜计划 (JSON)
┌─────────────────────────────────────────────┐
│  Phase 2：一致性管理层（实施中）                 │
│  • SceneConsistencyTracker — 跨镜头视觉锚点    │
│  • PromptEnhancer         — 专业镜头 prompt    │
│  • StyleReferenceManager  — 风格参考图管理      │
└─────────────────────────────────────────────┘
      ↓  增强型视频 prompt + 参考图
┌─────────────────────────────────────────────┐
│  视频生成层                                    │
│  • LeihuoVideo  (doubao-seedance-2-0)        │
│  • HunyuanVideo (本地 GPU, LoRA)             │
└─────────────────────────────────────────────┘
      ↓  各镜头视频片段
┌─────────────────────────────────────────────┐
│  Phase 3：后处理一致性修正层（规划中）            │
│  • InstantID   — 人脸锁定统一                  │
│  • ControlNeXt — 姿态/构图二次校正              │
└─────────────────────────────────────────────┘
      ↓
FFmpeg / Remotion 最终合成
```

---

## Phase 1：分镜智能规划层

**难度**：⭐（纯 prompt 工程 + Python，无新依赖）  
**状态**：✅ 已完成

### 新增文件

| 文件 | 功能 |
|------|------|
| `tools/planning/storyboard_planner.py` | LLM 自动分镜规划，输出结构化 JSON 镜头计划 |
| `tools/planning/character_sheet.py` | 角色一致性档案管理器 |
| `tools/planning/prompt_enhancer.py` | 专业镜头语言 prompt 增强器 |
| `skills/core/cinematography-director.md` | 导演级镜头知识库（景别、运镜、光效词汇） |

### 核心能力

- 景别自动选择：ECU / CU / MCU / MS / WS / EWS / Aerial
- 运镜规划：static / dolly-in / dolly-out / pan / crane / handheld
- 情绪光效：high-key / low-key / practical / golden-hour / cold-blue
- 角色锚点：在所有包含该角色的镜头 prompt 中自动注入外观描述

### 使用方式

```python
from tools.planning.storyboard_planner import StoryboardPlanner
from tools.planning.character_sheet import CharacterSheet

# 1. 登记角色
chars = CharacterSheet()
chars.add("Dr. Chen", "Asian female scientist, 35, short black hair, white lab coat, determined eyes")

# 2. 生成分镜计划
planner = StoryboardPlanner()
result = planner.execute({
    "treatment": "2157年，科学家接收到外星文明的最后信号...",
    "target_duration": 30,
    "genre": "sci-fi drama",
    "mood": "contemplative, awe-inspiring",
    "characters": chars.export(),
    "shot_count": 6,
})

# 3. 生成增强 prompt
for shot in result.data["shots"]:
    print(shot["video_prompt"])  # 已注入专业镜头语言
```

---

## Phase 2：一致性管理层

**难度**：⭐⭐（需要 Jellyfish 思路，Python 集成）  
**状态**：✅ 已完成

### 新增文件

| 文件 | 功能 |
|------|------|
| `tools/planning/scene_consistency.py` | 跨镜头视觉锚点追踪（受 Jellyfish 启发） |

### 核心能力

- **风格锚点**：从第一个生成镜头提取视觉描述符，后续镜头自动继承
- **角色锚点**：主角外观描述在所有涉及该角色的镜头中保持一致
- **场景锚点**：同一场景的光效、色调、环境元素保持连贯
- **负面 prompt 继承**：避免在同一部片中出现矛盾的视觉元素

---

## Phase 3：后处理一致性修正层

**难度**：⭐⭐⭐（需要 GPU，安装 InstantID / ControlNeXt）  
**状态**：🔲 规划中

### 计划新增

| 工具 | 依赖 | 功能 |
|------|------|------|
| `tools/enhancement/instantid_facelock.py` | InstantID + GPU | 用参考图统一所有镜头中的人物面孔 |
| `tools/enhancement/controlnext_compose.py` | ControlNeXt + GPU | 按分镜计划的构图要求重新生成镜头 |
| `tools/video/hunyuan_lora_video.py` | HunyuanVideo 1.5 + GPU | LoRA 微调锁定角色一致性 |

### 安装条件

```bash
# 需要 NVIDIA GPU (VRAM >= 16GB)
pip install -r requirements-gpu.txt
# 下载 InstantID 模型权重
# 下载 HunyuanVideo 1.5 模型
```

---

## 更新日志

| 时间 | 变更 |
|------|------|
| 2026-06-30 | 完成调研，确定三阶段升级路线图 |
| 2026-06-30 | Phase 1 完成：StoryboardPlanner + CharacterSheet + PromptEnhancer |
| 2026-06-30 | Phase 1 完成：cinematography-director.md 导演知识库技能文件 |
| 2026-06-30 | Phase 2 完成：SceneConsistencyTracker 跨镜头视觉锚点系统 |
| 2026-06-30 | 修复 leihuo_video.py 端点 `/v1/video/generations` 及响应解析 |
| 2026-06-30 | 修复 leihuo_image.py 最小像素限制（SeeDream 要求 ≥ 3,686,400px） |
| 2026-06-30 | 修复 piper_tts.py 添加 `--data-dir` 参数 |
| 2026-06-30 | Phase 1+2 全部工具通过注册系统验证（5/5 available） |
| 2026-06-30 | StoryboardPlanner 真实运行验证：生成《最后的信号》6镜头专业分镜方案 |
| 2026-06-30 | 修复 StoryboardPlanner：Claude 模型须用 Anthropic SDK，非 OpenAI SDK |
| 2026-06-30 | Phase 3 骨架完成：InstantID face-lock（待 GPU 环境激活） |
| 2026-06-30 | 用新分镜方案重新提交视频生成任务（brwpzzqeh，进行中） |
