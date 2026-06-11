# PCSE 完整参数清单

> 包含运行一次 WOFOST 模拟所需的全部输入参数，按模块分组

---

## 1. 天气数据 (Weather)

每条记录覆盖一天，共 12 个字段。

| 字段 | 类型 | 单位 | 说明 | 示例值 |
|------|------|------|------|--------|
| `DAY` | date | YYYY-MM-DD | 日期 | 2000-01-01 |
| `LAT` | float | ° | 纬度 | 37.64 |
| `LON` | float | ° | 经度 | -6.09 |
| `ELEV` | float | m | 海拔 | 50 |
| `TMAX` | float | °C | 日最高气温 | 20.9 |
| `TMIN` | float | °C | 日最低气温 | 10.9 |
| `VAP` | float | hPa | 水汽压 | 11.0 |
| `WIND` | float | m/s | 风速 (2m高度) | 3.2 |
| `RAIN` | float | cm/day | 降雨量 | 0.0 |
| `IRRAD` | float | W/m² | 入射短波辐射 | 9963 |
| `E0` | float | cm/day | 开放水面蒸发量 | 0.24 |
| `ES0` | float | cm/day | 裸土蒸发量 | 0.21 |
| `ET0` | float | cm/day | 参考蒸散量 | 0.24 |
| `SNOWDEPTH` | float\|None | cm | 雪深 (可空) | 0.0 |

**来源**：
- CGMS 数据库 `grid_weather` 表 (欧洲)
- NASA Power API (全球, 0.5°分辨率)
- 本地 Excel/CSV 文件

---

## 2. 土壤参数 (Soil)

共 8 个物理参数，定义土壤水分保持和传导特性。

| 参数代码 | 单位 | 说明 | 典型范围 | 示例 (壤土) |
|----------|------|------|----------|-------------|
| `SMFCF` | cm³/cm³ | 田间持水量 | 0.15-0.35 | 0.3175 |
| `SM0` | cm³/cm³ | 饱和含水量 | 0.35-0.50 | 0.4155 |
| `SMW` | cm³/cm³ | 凋萎点含水量 | 0.03-0.20 | 0.1515 |
| `CRAIRC` | cm³/cm³ | 临界空气含量 | 0.05-0.10 | 0.06 |
| `K0` | cm/day | 饱和导水率 | 5-100 | 10.0 |
| `SOPE` | cm/day | 根区最大渗透率 | 5-50 | 10.0 |
| `KSUB` | cm/day | 底土最大渗透率 | 5-50 | 10.0 |
| `RDMSOL` | cm | 最大根区深度 | 30-150 | 60.0 |

**参数关系**：`SMW < SMFCF < SM0`

**来源**：
- CGMS 数据库 `soil_physical_group` 表 (键值对模式)
- 田间实测
- 土壤质地分类推断 (沙土/壤土/粘土)

---

## 3. 场地参数 (Site)

共 6 个参数，定义地块的水文初始条件和运行方式。

| 参数代码 | 单位 | 说明 | 典型值 | 示例 |
|----------|------|------|--------|------|
| `IFUNRN` | — | 径流计算方案 (0=不计算, 1=计算) | 0/1 | 0 |
| `SSMAX` | cm | 最大地表蓄水 | 0-5 | 0 |
| `NOTINF` | — | 非入渗比例 | 0-1 | 0 |
| `SSI` | cm | 初始地表蓄水量 | 0-2 | 0 |
| `WAV` | cm | 初始有效水分 (播种时土壤剖面有效水) | 5-30 | 10 |
| `SMLIM` | cm³/cm³ | 土壤水分下限 (低于此值无蒸腾) | 0.1-0.3 | 0.25 |

---

## 4. 作物参数 (Crop)

分为 **标量参数** (42个) 和 **表格参数** (12个，每个含多行DVS→Value映射)。

### 4.1 物候与温度参数 (Phenology & Temperature)

| 参数代码 | 单位 | 说明 | 冬小麦示例 |
|----------|------|------|------------|
| `TSUMEM` | °C·d | 播种→出苗积温需求 | 0 |
| `TSUM1` | °C·d | 出苗→开花积温需求 (营养生长期) | 随品种: 518-852 |
| `TSUM2` | °C·d | 开花→成熟积温需求 (生殖生长期) | 随品种: 481-877 |
| `TBASEM` | °C | 出苗前基础温度 (低于此温不发育) | -10 |
| `TBASE` | °C | 出苗后基础温度 | 0 |
| `TEFFMX` | °C | 最高有效温度 (高于此温不额外加速) | 30 |
| `DVSEND` | — | 成熟时发育阶段值 (固定) | 2.0 |
| `DVSI` | — | 初始发育阶段 (固定) | 0.0 |
| `DLC` | h | 临界日长 (短日照作物开花条件) | -99 (=不敏感) |
| `DLO` | h | 最适日长 (长日照作物开花条件) | -99 (=不敏感) |
| `IDSL` | 0/1 | 是否启用生长季直射/散射光分离 | 0 |
| `SPA` | cm | 根区潜在有效水量 | 0 |
| `SPAN` | kg N/ha | 生命周期总吸氮量 | 31.3 |
| `PERDL` | day⁻¹ | 叶片最大相对死亡率 (衰老) | 0.03 |
| `RDI` | cm | 播种时初始根深 | 10 |
| `RRI` | cm/day | 根深最大日增速率 | 1.2 |
| `RDMCR` | cm | 最大根深 (品种上限) | 125 |
| `DEPNR` | — | 作物群体依赖系数 (养分吸收) | 4.5 |

### 4.2 光合与呼吸参数 (Photosynthesis & Respiration)

| 参数代码 | 单位 | 说明 | 冬小麦示例 |
|----------|------|------|------------|
| `EFF` | kg/(ha·h·J/m²·s) | 单叶片光能初始利用效率 | 0.45 |
| `KDIF` | — | 散射光消减系数 | 0.6 |
| `LAIEM` | m²/m² | 出苗时叶面积指数 | 0.1365 |
| `RGRLAI` | °C⁻¹·day⁻¹ | 叶面积指数最大相对增长率 | 0.00817 |
| `Q10` | — | 呼吸作用Q10温度系数 | 2.0 |
| `RML` | kg/(kg·day) | 叶片维持呼吸相对速率 | 0.03 |
| `RMO` | kg/(kg·day) | 储存器官维持呼吸相对速率 | 0.01 |
| `RMR` | kg/(kg·day) | 根系维持呼吸相对速率 | 0.015 |
| `RMS` | kg/(kg·day) | 茎秆维持呼吸相对速率 | 0.015 |
| `IOX` | — | 氧胁迫系数 | — |
| `IAIRDU` | 0/1 | 根系有无空气管道 (水稻=1, 旱作=0) | 0 |
| `CFET` | — | 蒸散校正因子 | 1.0 |
| `TDWI` | kg/ha | 播种时初始总干物重 | 210 |

### 4.3 干物质分配系数 (Conversion Efficiencies)

| 参数代码 | 单位 | 说明 | 冬小麦示例 |
|----------|------|------|------------|
| `CVL` | kg/kg | 同化物→叶片转化效率 | 0.685 |
| `CVO` | kg/kg | 同化物→储存器官转化效率 | 0.709 |
| `CVR` | kg/kg | 同化物→根系转化效率 | 0.694 |
| `CVS` | kg/kg | 同化物→茎秆转化效率 | 0.662 |

### 4.4 表格参数 (DVS-Value 映射表)

每个表参数最多 10 行 (`_01` ~ `_10`)，X 轴为 DVS，Y 轴为参数值。末尾行用 (0,0) 填充。

| 参数前缀 | 说明 | 单位 | 冬小麦数据格式 |
|----------|------|------|---------------|
| `AMAXTB` | 最大CO₂同化速率 | kg/(ha·h) | (DVS, AMAX) 对，如 (0,35.83), (1,35.83), (1.3,35.83), (2,4.48) |
| `SLATB` | 比叶面积 | ha/kg | (DVS, SLA) 对 |
| `FLTB` | 叶片分配系数 (新生同化物去叶片的比例) | — | (DVS, fraction) 对 |
| `FSTB` | 茎秆分配系数 | — | (DVS, fraction) 对 |
| `FOTB` | 储存器官分配系数 | — | (DVS, fraction) 对 |
| `FRTB` | 根系分配系数 | — | (DVS, fraction) 对 |
| `RDRRTB` | 根系相对死亡率 | — | (DVS, rate) 对 |
| `RDRSTB` | 茎秆相对死亡率 | — | (DVS, rate) 对 |
| `RFSETB` | 根冠比降低因子 (水分胁迫下) | — | (DVS, factor) 对 |
| `DTSMTB` | 日平均温度对发育速率的影响 | °C | (Tavg, 影响因子) 对 |
| `TMNFTB` | 最低温度对同化速率的影响 | °C | (Tmin, 影响因子) 对 |
| `TMPFTB` | 霜冻致死临界温度 | °C | (DVS, 临界温度) 对 |

**注意**：代码运行时做了三个转换：
- `SSA` (单值) → `SSATB: [0, SSA, 2.0, SSA]`
- `KDIF` (单值) → `KDIFTB: [0, KDIF, 2.0, KDIF]`
- `EFF` (单值) → `EFFTB: [0, EFF, 40.0, EFF]`

### 4.5 品种参数覆盖 (Variety Override)

与标量参数相同参数代码，存在 `variety_parameter_value` 时覆盖 `crop_parameter_value` 的默认值。典型覆盖项：

| 参数 | 品种差异说明 |
|------|-------------|
| `TSUM1` | 不同品种营养生长期天数不同 |
| `TSUM2` | 不同品种灌浆期天数不同 |
| `EFF` | 品种间光合效率差异 |
| `SPAN` | 品种间吸氮量差异 |

---

## 5. 农事操作 (Agromanagement)

### 5.1 完整结构

```yaml
AgroManagement:
- <活动开始日期>:
    CropCalendar:    # 必填，定义这一季的作物起止
    TimedEvents:     # 选填，按日历日期触发的操作
    StateEvents:     # 选填，按作物/土壤状态触发的操作
```

### 5.2 CropCalendar 字段

| 字段 | 必填 | 说明 | 可选值 |
|------|------|------|--------|
| `crop_name` | 是 | 作物名称 | 任意字符串 |
| `variety_name` | 是 | 品种名称 | 任意字符串 |
| `crop_start_date` | 是 | 播种/出苗日期 | YYYY-MM-DD |
| `crop_start_type` | 是 | 起始类型 | `sowing` / `emergence` |
| `crop_end_date` | 条件 | 收获日期 | YYYY-MM-DD 或 null |
| `crop_end_type` | 是 | 结束类型 | `maturity` / `harvest` / `earliest` |
| `max_duration` | 是 | 最长天数 (保底) | 整数 |

### 5.3 TimedEvents 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `event_signal` | 是 | 操作类型: `irrigate` / `apply_n` / `apply_npk` / `mowing` / `terminate` |
| `name` | 否 | 事件名称 (注释) |
| `comment` | 否 | 事件说明 (注释) |
| `events_table` | 是 | 日期→参数字典列表 |

### 5.4 StateEvents 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `event_signal` | 是 | 操作类型，同 TimedEvents |
| `event_state` | 是 | 监控的状态变量: `DVS` / `SM` |
| `zero_condition` | 是 | 触发方向: `rising` / `falling` / `either` |
| `name` | 否 | 事件名称 |
| `comment` | 否 | 事件说明 |
| `events_table` | 是 | 阈值→参数字典列表 |

### 5.5 操作信号与参数

| 信号 | 可用参数 | 单位 |
|------|---------|------|
| `irrigate` | `amount` (灌水量), `efficiency` (灌溉效率0-1) | cm |
| `apply_n` | `amount` 或 `N_amount` (施氮量), `recovery` 或 `N_recovery` (利用率0-1) | g/m² 或 kg/ha |
| `apply_npk` | `N_amount`, `P_amount`, `K_amount` | g/m² 或 kg/ha |
| `mowing` | `biomass_remaining` (留茬干物重) | kg/ha |
| `terminate` | 无 | — |

---

## 6. 模拟输出 (Output)

### 6.1 逐日输出变量

| 变量 | 单位 | 说明 |
|------|------|------|
| `DVS` | — | 发育阶段 (0=出苗, 1=开花, 2=成熟) |
| `LAI` | m²/m² | 叶面积指数 |
| `TAGP` | kg/ha | 总地上生物量 |
| `TWSO` | kg/ha | 储存器官总干重 (籽粒/块茎) |
| `TWLV` | kg/ha | 叶片总干重 |
| `TWST` | kg/ha | 茎秆总干重 |
| `TWRT` | kg/ha | 根系总干重 |
| `TRA` | cm | 实际蒸腾量 (逐日累计) |
| `RD` | cm | 当前根深 |
| `SM` | — | 土壤水分含量 (体积比) |
| `RFTRA` | — | 蒸腾削减因子 (1=无胁迫) |

### 6.2 全季摘要输出

| 变量 | 单位 | 说明 |
|------|------|------|
| `DVS` | — | 最终发育阶段 |
| `LAIMAX` | m²/m² | 全季最大叶面积指数 |
| `TAGP` | kg/ha | 最终总地上生物量 |
| `TWSO` | kg/ha | 最终经济产量 |
| `TWLV` | kg/ha | 最终叶片干重 |
| `TWST` | kg/ha | 最终茎秆干重 |
| `TWRT` | kg/ha | 最终根系干重 |
| `CTRAT` | — | 蒸腾蒸散比 |
| `RD` | cm | 最终根深 |
| `DOS` | date | 播种日期 |
| `DOE` | date | 出苗日期 |
| `DOA` | date | 开花日期 |
| `DOM` | date | 成熟日期 |
| `DOH` | date | 收获日期 |
| `DOV` | date | (附加日期) |

---

## 7. 完整参数文件结构总览

```
一次 PCSE 模拟需要的全部输入
=============================

┌── Weather (天气)
│   ├── 逐日数据: DAY, TMAX, TMIN, VAP, WIND, RAIN, IRRAD, E0, ES0, ET0, SNOWDEPTH
│   └── 位置信息: LAT, LON, ELEV
│
├── Soil (土壤)  
│   └── 8参数: SMFCF, SM0, SMW, CRAIRC, K0, SOPE, KSUB, RDMSOL
│
├── Site (场地)
│   └── 6参数: IFUNRN, SSMAX, NOTINF, SSI, WAV, SMLIM
│
├── Crop (作物)
│   ├── 物候温度: TSUMEM, TSUM1, TSUM2, TBASEM, TBASE, TEFFMX, DVSEND, DVSI, DLC, DLO, IDSL, SPA, SPAN, PERDL, RDI, RRI, RDMCR, DEPNR (18个)
│   ├── 光合呼吸: EFF, KDIF, LAIEM, RGRLAI, Q10, RML, RMO, RMR, RMS, IOX, IAIRDU, CFET, TDWI (13个)
│   ├── 转化效率: CVL, CVO, CVR, CVS (4个)
│   ├── 表格参数: AMAXTB, SLATB, FLTB, FSTB, FOTB, FRTB, RDRRTB, RDRSTB, RFSETB, DTSMTB, TMNFTB, TMPFTB (12个, 各10行)
│   └── 品种覆盖: TSUM1, TSUM2, EFF, SPAN 等 (可选, 覆盖作物默认值)
│
└── Agromanagement (农事)
    ├── Campaign (活动周期) × N
    │   ├── CropCalendar: crop_name, crop_start_date, crop_start_type, crop_end_date, crop_end_type, max_duration
    │   ├── TimedEvents × N: event_signal, events_table[{date: {params}}]
    │   └── StateEvents × N: event_signal, event_state, zero_condition, events_table[{threshold: {params}}]
    └── 尾部空活动 (模拟结束标记)

合计: 1天气文件 + ~60个标量参数 + 12×10个表格点 + 农事YAML
```

---

## 8. 数据来源速查

| 数据 | 存储位置 | 格式 | 说明 |
|------|---------|------|------|
| 天气 | `grid_weather` 表 / NASA Power API / Excel / CSV | DB/API/文件 | 逐日 11 要素 |
| 土壤 | `soil_physical_group` 表 / 实测 | DB 键值对 / 字典 | 8 参数 |
| 场地 | `site` 表 / 实测 | DB / 字典 | 6 参数 |
| 作物默认值 | `crop_parameter_value` 表 / CABO 文件 | DB 键值对 / 文本文件 | 42 标量 + 12 表 |
| 品种覆盖值 | `variety_parameter_value` 表 | DB 键值对 | 覆盖默认值 |
| 农事操作 | `crop_calendar` 表 / YAML 文件 | DB 行 → YAML / 手写 YAML | 基本或完整 |
