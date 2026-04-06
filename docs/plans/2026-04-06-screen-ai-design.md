# 局域网可查看的屏幕拍摄 AI 分析工具设计

**日期：** 2026-04-06

**目标：**  
构建一个简洁的 Python 工具：在 Windows 上通过全局热键触发，从 Android IP Camera 的 MJPEG 视频流中抓取短时间窗口内的多帧图像，自动选出最稳定的一帧，进行电脑屏幕检测与梯形校正，将校正后的完整屏幕图发送给视觉大模型分析，并通过局域网网页向不同设备展示最新结果与历史记录。

## 范围

第一版只做以下能力：

- Windows 全局热键触发，且不受窗口焦点影响
- 从 Android IP Camera 的 MJPEG 流中抓取多帧
- 基于轻量规则自动选择最佳帧
- 使用 OpenCV 进行屏幕四边形检测与透视校正
- 调用可配置的视觉大模型接口获取文本分析
- 提供局域网网页查看最新结果与近期历史
- 本地文件保存结果，不使用数据库

第一版明确不做：

- 数据库
- 用户登录与鉴权
- 多用户并发任务
- WebSocket
- 深度学习屏幕检测
- 视频稳像和多帧融合
- 连续自动分析模式

## 方案比较

### 方案 A：单进程 Python 服务

单个 Python 进程同时承担热键监听、抓帧、选帧、梯形校正、AI 调用和 Web 页面提供。

优点：

- 结构最简单
- 第一版落地最快
- 部署与调试成本最低

缺点：

- 后期如果扩成多数据源，需要再拆模块或进程

### 方案 B：采集分析与 Web 分离

将采集分析和网页服务拆成两个进程。

优点：

- 职责分离更清晰
- 后期扩展性更好

缺点：

- 第一版会引入不必要的状态同步复杂度

### 结论

选择 **方案 A：单进程 Python 服务**，但内部按模块化方式组织，保证未来仍可拆分。

## 核心架构

程序启动后完成两件事：

1. 启动局域网 Web 服务
2. 注册全局热键监听

按下热键后，如果当前没有任务在执行，则启动一次采集分析任务。任务流程如下：

1. 从 MJPEG 流中抓取约 8 帧
2. 对每帧进行屏幕候选检测和评分
3. 选择最稳定且最清晰的最佳帧
4. 对最佳帧执行梯形校正，得到完整屏幕图
5. 调用视觉大模型分析校正图
6. 保存原图、调试图、校正图和分析结果
7. 页面轮询显示最新状态和结果

## 模块设计

### `stream_client`

职责：

- 连接 MJPEG 地址
- 解析 JPEG 帧
- 在触发时抓取限定数量的帧

约束：

- 每次触发只抓取一个很短的时间窗口
- 发生超时、连接失败、帧损坏时抛出明确错误

### `frame_selector`

职责：

- 对候选帧进行轻量评分并选出最佳帧

评分维度：

- `sharpness_score`：拉普拉斯方差，评估模糊程度
- `quad_score`：屏幕四边形可信度
- `stability_score`：与相邻帧角点变化是否平稳

建议总分：

`total = 0.45 * sharpness + 0.40 * quad + 0.15 * stability`

### `screen_rectifier`

职责：

- 检测画面中的电脑屏幕四边形
- 通过透视变换输出完整屏幕图像

第一版算法：

- 图像缩放
- 灰度化
- 高斯模糊
- Canny 边缘检测
- 轮廓搜索
- 过滤凸四边形
- 按面积、长宽比、近矩形程度评分
- 选最佳四边形
- 使用 `getPerspectiveTransform` 与 `warpPerspective`

### `ai_analyzer`

职责：

- 把校正图发送给视觉模型
- 返回文本分析结果

接口要求：

- 支持配置 `provider`、`base_url`、`api_key`、`model`、`prompt`
- 第一版优先兼容 OpenAI 风格的图片分析接口
- 记录请求耗时与失败原因

### `job_controller`

职责：

- 接收热键触发
- 确保同一时间只执行一个任务
- 管理状态与保存结果

状态集合：

- `idle`
- `capturing`
- `rectifying`
- `analyzing`
- `success`
- `error`

### `web_server`

职责：

- 提供局域网页面和简单 JSON API
- 展示当前状态、最新结果和历史记录

建议接口：

- `GET /`：页面
- `GET /api/status`：当前状态
- `GET /api/latest`：最新结果
- `GET /api/history`：近期历史
- `/images/...`：静态结果图

## 数据与目录

项目目录保持简洁：

```text
面试code/
  app.py
  config.yaml
  requirements.txt
  README.md
  docs/
    plans/
  src/
    hotkey_listener.py
    stream_client.py
    frame_selector.py
    screen_rectifier.py
    ai_analyzer.py
    state_store.py
    web_server.py
    models.py
  data/
    captures/
    rectified/
    debug/
    results/
```

## 配置

使用单一 `config.yaml`：

- `stream_url`
- `hotkey`
- `server_host`
- `server_port`
- `capture_frame_count`
- `capture_timeout_sec`
- `output_dir`
- `history_limit`
- `analysis_prompt`
- `ai.provider`
- `ai.base_url`
- `ai.api_key`
- `ai.model`
- `ai.verify_ssl`

## 失败处理

### 抓流失败

- 页面显示错误原因
- 不阻塞下一次热键触发

### 屏幕检测失败

- 保存最佳候选原图和调试图
- 页面显示“屏幕检测失败”

### AI 调用失败

- 保留校正图
- 页面显示“图片已获取，但 AI 分析失败”

## 验证策略

按以下顺序验证：

1. 单独验证 MJPEG 抓帧
2. 单独验证屏幕检测与梯形校正
3. 单独验证 AI 调用
4. 验证热键触发整条链路
5. 验证局域网网页访问

## 已知限制

- 当前目录不是 git 仓库，因此本轮无法按流程提交设计文档 commit
- Android IP Camera 提供的 HTTPS 地址可能存在自签名证书问题，需要配置允许关闭 SSL 验证
- 第一版屏幕检测依赖传统图像处理，对强反光或屏幕边缘不可见场景不保证成功率
