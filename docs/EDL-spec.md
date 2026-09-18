"""EDL 字段规格（定稿 v4.0 §3）

## 定位
EDL（Edit Decision List）是贯穿全局的唯一数据源：
自动剪辑规则引擎「自动成片 / 换个剪法」生成它 → 手动编辑器轻编辑修改它 →
FFmpeg 渲染 Worker 消费它。存储在 `timelines` 表，(project_id, version) 唯一，
每次自动成片 / 手动保存 / 换剪法都产生新快照 version+1，历史可回溯。

## 演示口径（与 5 页原型一致）
6 段素材 3 分 15 秒 → 成片 4 段 1:52（18+22+34+38s，叠化转场重叠各扣 durMs）；
转场 叠化×2 + 推近×1，位置 00:18 / 00:40 / 01:14；
配乐「暮色公路」96% 匹配，82 BPM → 拍间隔 732ms，切点吸附容差 ±150ms。

## JSON 结构
```json
{
  "version": 1,
  "meta": {
    "title": "周末出走计划",
    "aspect": "9:16",
    "fps": 30,
    "seed": 7,
    "preference": {"duration": "fit", "transitionStyle": "gentle"}
  },
  "clips": [
    {"assetId": 1, "inMs": 12400, "outMs": 30600, "note": "开场 · 片头淡入",
     "fadeInMs": 800, "fadeOutMs": 0}
  ],
  "transitions": [
    {"afterClip": 1, "type": "dissolve", "durMs": 800, "beatAligned": true}
  ],
  "audio": {"musicId": 7, "volume": 0.65, "offsetMs": 38000,
            "fadeInMs": 1500, "fadeOutMs": 2000},
  "captions": [{"text": "周末出走计划 · 闪剪AI", "startMs": 109000,
                "endMs": 112000, "style": "ending_credit"}]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| meta.aspect | 16:9/9:16/1:1 | 画幅偏好，渲染端决定 scale/crop |
| meta.fps | 30/60 | 输出帧率 |
| meta.seed | int? | 「换个剪法」固定 audio 换 seed 重排 |
| meta.preference.duration | 45s/full/fit | 成片时长偏好（fit=AI 适配，如 1:52） |
| meta.preference.transitionStyle | gentle/dynamic/minimal | 转场风格，参与转场决策 |
| clips[].inMs/outMs | ms | 原片出入点，outMs > inMs |
| clips[].note | str | 生成依据文案，直接展示在「AI 是这么排的」 |
| transitions[].afterClip | 1-based | 第 N 段与第 N+1 段之间的剪辑点；< len(clips) |
| transitions[].beatAligned | bool | 切点是否吸附鼓点（732ms 拍格 ±150ms） |
| audio.offsetMs | ms | 音乐起点偏移，副歌对齐用（如副歌 38s 处） |
| captions[].style | ending_credit/subtitle/title | 片尾署名 / 字幕 / 标题 |

## 派生量（服务端统一计算，前端只展示）
- 总时长 = Σ(out-in) − Σ(非 none 转场 durMs) → 信息卡「01:52」
- 使用片段数 / 裁掉时长 → 信息卡「4 段 · 裁掉 1:23」
- 转场摘要 → 信息卡「叠化×2 · 推近×1」
"""
