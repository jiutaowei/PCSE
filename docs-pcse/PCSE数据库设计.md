# PCSE 数据库设计

> PCSE (Python Crop Simulation Environment) v6.0.13 — Wageningen University
> Demo 数据库位置：`~/.pcse/pcse.db`（首次使用时从 `pcse_dump.sql` 自动构建）
> SQL 转储源文件：`pcse/tests/test_data/pcse_dump.sql`

---

## 整体架构

PCSE 数据库采用 **SQLite** 存储，包含 15 张业务表，按功能分为 6 个模块：

```
空间参考 (grid)
    │
    ├── 天气数据 (grid_weather, ensemble_grid_weather)
    ├── 场地数据 (site)
    ├── 土壤数据 (soil_type → soil_layers → soil_physical_group)
    ├── 作物数据 (crop → crop_parameter_value + variety_parameter_value)
    │         │
    │         └── 作物日历 (crop_calendar)
    │
    └── 模拟输出 (sim_results_timeseries, sim_results_summary)

工具表 (tasklist, wofost_unittest_benchmarks)
```

核心设计理念：
- **网格驱动**：所有数据通过 `grid_no` 锚定到空间网格点
- **键值对存储**：作物参数和土壤物理属性采用 `(主键, parameter_code) → parameter_xvalue / parameter_yvalue` 模式，新增参数无需 ALTER TABLE
- **继承+覆盖**：`crop_parameter_value`（默认值）→ `variety_parameter_value`（品种覆盖值）

---

## 1. 空间参考

### `grid` — 空间模拟网格点

CGMS (Crop Growth Monitoring System) 定义的 25km 分辨率网格。每个网格点代表一个模拟的独立空间单元。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `grid_no` | INTEGER | **PK** | 网格编号（如 31031 = 西班牙 Sevilla） |
| `latitude` | NUMERIC(10,5) | NOT NULL | 纬度（°） |
| `longitude` | NUMERIC(10,5) | NOT NULL | 经度（°） |
| `altitude` | NUMERIC(10,5) | NOT NULL | 海拔（m） |
| `climate_barrier_no` | INTEGER | NOT NULL | 气候屏障编号 |
| `distance_to_coast` | NUMERIC(10,5) | NOT NULL | 距海岸距离（km） |

示例数据：
| grid_no | latitude | longitude | altitude |
|---------|----------|-----------|----------|
| 1 | 40.18 | -0.14 | 327 |
| 31031 | 37.64 | -6.09 | — |
| 35042 | — | — | — |

---

## 2. 天气数据

### `grid_weather` — 逐日气象数据

每个网格 + 每天的完整气象要素。数据来源为 CGMS MARS 气象数据库，经过插值到各网格点。

| 列名 | 类型 | 约束 | 说明 | 单位 |
|------|------|------|------|------|
| `grid_no` | INTEGER | **PK** | 网格编号 | — |
| `day` | DATE | **PK** | 日期 | YYYY-MM-DD |
| `maximum_temperature` | NUMERIC(10,5) | NOT NULL | 最高气温 | °C |
| `minimum_temperature` | NUMERIC(10,5) | NOT NULL | 最低气温 | °C |
| `vapour_pressure` | NUMERIC(10,5) | NOT NULL | 水汽压 | hPa |
| `windspeed` | NUMERIC(10,5) | NOT NULL | 风速（10m 高度） | m/s |
| `rainfall` | NUMERIC(10,5) | NOT NULL | 降雨量 | mm/day |
| `e0` | NUMERIC(10,5) | NOT NULL | 开放水面蒸发量 | mm/day |
| `es0` | NUMERIC(10,5) | NOT NULL | 裸土蒸发量 | mm/day |
| `et0` | NUMERIC(10,5) | NOT NULL | 参考蒸散量 | mm/day |
| `calculated_radiation` | INTEGER | NOT NULL | 计算辐射（存储值需 ×1000） | W/m² × 1000 |
| `snow_depth` | NUMERIC(10,5) | NULL | 雪深 | cm |

**数据加载时的单位转换**（在 `GridWeatherDataProvider._make_WeatherDataContainer()` 中）：
- `WIND`：10m → 2m（`wind10to2()` 函数转换）
- `RAIN`：除以 10（cm → mm？实际为 mm/day 值缩小至 cm）
- `IRRAD`：×1000（存储值恢复为 W/m²）
- `E0/ES0/ET0`：除以 10

示例数据（grid 31031）：
| day | TMAX | TMIN | VAP | RAIN |
|-----|------|------|-----|------|
| 1999-12-01 | 20.9 | 10.9 | 11.0 | 0 |
| 1999-12-02 | 21.9 | 11.4 | 13.1 | 0 |
| 1999-12-04 | 15.2 | 12.9 | 15.5 | 0.5 |

### `ensemble_grid_weather` — 集合预报天气数据

用于不确定性分析的集合预报结果。目前仅存储降雨量。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `grid_no` | INTEGER | **PK** | 网格编号 |
| `day` | DATE | **PK** | 日期 |
| `member_id` | INTEGER | **PK** | 集合成员编号（0-50） |
| `rainfall` | NUMERIC(10,5) | NOT NULL | 该成员的降雨量 |

---

## 3. 场地数据

### `site` — 地形与水文本地参数

每个网格+年份的场地特性，影响水分平衡计算。

| 列名 | 类型 | 约束 | 说明 | 对应 WOFOST 参数 |
|------|------|------|------|-------------------|
| `grid_no` | INTEGER | **PK** | 网格编号 | — |
| `year` | INTEGER | **PK** | 年份 | — |
| `ifunrn` | INTEGER | NOT NULL | 径流方案（0=不计算径流） | `IFUNRN` |
| `max_surface_storage` | NUMERIC(10,5) | NOT NULL | 最大地表蓄水 | `SSMAX` |
| `not_infiltrating_fraction` | NUMERIC(10,5) | NOT NULL | 非入渗比例 | `NOTINF` |
| `initial_surface_storage` | NUMERIC(10,5) | NOT NULL | 初始地表蓄水 | `SSI` |
| `inital_water_availability` | NUMERIC(10,5) | NOT NULL | 初始有效水分 | `WAV` |
| `smlim` | NUMERIC(10,5) | NULL | 土壤水分下限 | `SMLIM` |

示例数据：
| grid_no | year | WAV | SMLIM |
|---------|------|-----|-------|
| 31031 | 2000 | 10 | 0.25 |
| 35042 | 2000 | 22 | 0.179 |
| 1 | 1965 | 22 | 0.179 |

---

## 4. 土壤数据

三层结构：**土壤类型 → 土壤层次 → 物理参数**

### `soil_type` — 网格到土壤类型的映射

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `grid_no` | INTEGER | **PK** | 网格编号 |
| `soil_type_no` | INTEGER | NOT NULL | 土壤类型编号 |

### `soil_layers` — 土层定义

每个土壤类型可以有一个或多个层次（最多 6 层）。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `soil_type_no` | INTEGER | **PK** | 土壤类型编号 |
| `layer_no` | INTEGER | **PK** | 层次序号（从 1 开始） |
| `thickness` | NUMERIC(10,5) | NULL | 土层厚度（cm） |
| `soil_group_no` | INTEGER | NULL | 土壤物理分组编号 |

**注意**：PCSE Demo 数据库仅支持 **单层土壤**（`fetch_soildata()` 强制检查 `len(rows) == 1`）。多层数据存在但使用 `fetch_soiltype_multilayer` 另有函数处理。

示例：
| soil_type_no | layer_no | thickness | soil_group_no |
|-------------|----------|-----------|---------------|
| 1 | 1 | 60 | 449 |
| 2 | 1 | 10 | 1 |
| 2 | 2 | 10 | 1 |
| 2 | 3 | 10 | 1 |
| 2 | 4 | 20 | 1 |
| 2 | 5 | 30 | 1 |
| 2 | 6 | 45 | 1 |

### `soil_physical_group` — 土壤物理参数（键值对）

土壤物理属性采用与作物参数相同的键值对模式。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `soil_group_no` | INTEGER | **PK** | 土壤物理分组编号 |
| `parameter_code` | VARCHAR(30) | **PK** | 参数代码 |
| `parameter_xvalue` | NUMERIC(10,5) | NOT NULL | 标量值（主值） |
| `parameter_yvalue` | NUMERIC(10,5) | NULL | 纵坐标值（表格参数时使用） |

**参数代码对照表**：

| 数据库参数代码 | WOFOST 参数 | 说明 | 典型值 |
|---------------|-------------|------|--------|
| `CRITICAL_AIR_CONTENT` | `CRAIRC` | 临界空气含量 | 0.06–0.09 |
| `HYDR_CONDUCT_SATUR` | `K0` | 饱和导水率 | 10–70 cm/d |
| `MAX_PERCOL_ROOT_ZONE` | `SOPE` | 根区最大渗透率 | 10–70 cm/d |
| `MAX_PERCOL_SUBSOIL` | `KSUB` | 底土最大渗透率 | 10–70 cm/d |
| `SOIL_MOISTURE_CONTENT_FC` | `SMFCF` | 田间持水量 | 0.179–0.318 |
| `SOIL_MOISTURE_CONTENT_SAT` | `SM0` | 饱和含水量 | 0.366–0.416 |
| `SOIL_MOISTURE_CONTENT_WP` | `SMW` | 萎蔫点含水量 | 0.036–0.152 |

---

## 5. 作物数据

### `crop` — 作物类型参考

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `crop_no` | INTEGER | **PK** | 作物编号 |
| `crop_name` | VARCHAR(40) | NOT NULL | 作物英文名 |
| `cropgroup_no` | INTEGER | NOT NULL | 作物分组（1=谷类, 2=根茎类, 3=玉米, 4=牧草） |
| `crop_model` | INTEGER | NOT NULL | 模型类型（0=WOFOST 籽粒, 1=WOFOST 生物量） |

完整作物列表：

| crop_no | crop_name | 中文 | cropgroup_no | crop_model |
|---------|-----------|------|-------------|------------|
| 1 | WINTER WHEAT | 冬小麦 | 1 | 0 |
| 2 | GRAIN MAIZE | 玉米 | 3 | 0 |
| 3 | SPRING BARLEY | 春大麦 | 1 | 0 |
| 5 | RICE | 水稻 | 1 | 0 |
| 6 | SUGAR BEETS | 糖用甜菜 | 2 | 0 |
| 7 | POTATO | 马铃薯 | 2 | 0 |
| 8 | FIELD BEANS | 蚕豆 | 1 | 0 |
| 9 | SOY BEAN | 大豆 | 1 | 0 |
| 10 | WINTER RAPESEED | 冬油菜 | 1 | 0 |
| 11 | SUNFLOWER | 向日葵 | 1 | 0 |
| 12 | FODDER MAIZE | 饲料玉米 | 4 | 1 |
| 13 | WINTER BARLEY | 冬大麦 | 1 | 0 |
| 14 | SPRING WHEAT | 春小麦 | 1 | 0 |
| 15 | SPRING RAPESEED | 春油菜 | 1 | 0 |
| 50 | FORAGE PERMANENT | 永久牧草 | 4 | 1 |
| 51 | FORAGE TEMPORARY | 临时牧草 | 4 | 1 |
| 99 | wheat_morocco | 摩洛哥小麦 | 1 | 0 |

### `crop_parameter_value` — 作物参数（键值对）

核心设计模式：**参数作为行存储，而非列**。每个参数一行，`parameter_code` 为参数名，`parameter_xvalue` 存标量值或表格 X 坐标，`parameter_yvalue` 存表格 Y 坐标。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `crop_no` | INTEGER | **PK** | 作物编号 |
| `parameter_code` | VARCHAR(20) | **PK** | 参数代码 |
| `parameter_xvalue` | NUMERIC(10,5) | NOT NULL | 标量值，或表格参数的 X 坐标 |
| `parameter_yvalue` | NUMERIC(10,5) | NULL | 表格参数的 Y 坐标（标量参数为 NULL） |

**标量参数（34 个）**：

| 参数代码 | 说明 | 单位 | 冬小麦值 |
|----------|------|------|----------|
| `CFET` | 蒸散校正因子 | — | 1.0 |
| `CVL` | 叶片同化物转化效率 | kg/kg | 0.685 |
| `CVO` | 储存器官同化物转化效率 | kg/kg | 0.709 |
| `CVR` | 根系同化物转化效率 | kg/kg | 0.694 |
| `CVS` | 茎秆同化物转化效率 | kg/kg | 0.662 |
| `DEPNR` | 作物群体依赖系数 | — | 4.5 |
| `DLC` | 临界日长 | h | -99（不适用） |
| `DLO` | 最适日长 | h | -99（不适用） |
| `DVSEND` | 发育阶段结束值 | — | 2.0 |
| `EFF` | 初始光能利用效率 | kg/ha·h/(J/m²·s) | 0.45 |
| `IAIRDU` | 空气管道是否存在于根中 | 0/1 | 0 |
| `IDSL` | 是否计算直射/散射光 | 0/1 | 0 |
| `KDIF` | 散射光滑减系数 | — | 0.6 |
| `LAIEM` | 出苗时叶面积指数 | m²/m² | 0.1365 |
| `PERDL` | 叶片最大相对死亡率 | — | 0.03 |
| `Q10` | 呼吸作用温度系数 | — | 2.0 |
| `RDI` | 初始根深 | cm | 10 |
| `RDMCR` | 最大根深 | cm | 125 |
| `RGRLAI` | 叶面积最大相对增长率 | °C⁻¹·d⁻¹ | 0.00817 |
| `RML` | 叶片维持呼吸速率 | kg/kg·d | 0.03 |
| `RMO` | 储存器官维持呼吸速率 | kg/kg·d | 0.01 |
| `RMR` | 根系维持呼吸速率 | kg/kg·d | 0.015 |
| `RMS` | 茎秆维持呼吸速率 | kg/kg·d | 0.015 |
| `RRI` | 根深最大日增长率 | cm/d | 1.2 |
| `SPA` | 根区最小有效水分 | cm | 0 |
| `SPAN` | 生命周期总吸氮量 | kg N/ha | 31.3 |
| `SSA` | 初始地表蓄水量 | cm | 0 |
| `TBASE` | 出苗后基础温度 | °C | 0 |
| `TBASEM` | 出苗前基础温度 | °C | -10 |
| `TDWI` | 初始总干物重 | kg/ha | 210 |
| `TEFFMX` | 最高有效温度 | °C | 30 |
| `TSUM1` | DVS 0→1 需积温 | °C·d | 随品种变 |
| `TSUM2` | DVS 1→2 需积温 | °C·d | 随品种变 |
| `TSUMEM` | 播种到出苗需积温 | °C·d | 随品种变 |
| `IOX` | 氧胁迫系数 | — | — |

**表格参数（12 个）**：参数代码以 `_NN` 后缀区分行号，X 为 DVS 坐标，Y 为对应参数值。

| 参数代码前缀 | 说明 | 行数 | 示例（冬小麦） |
|-------------|------|------|---------------|
| `AMAXTB` | 最大 CO₂ 同化速率随 DVS 变化 | 10 | (0, 35.83), (1.3, 35.83), (2, 4.48) |
| `DTSMTB` | 日平均温度影响系数 | 10 | (0, 0), (25, 25), (45, 25) |
| `FLTB` | 叶片分配系数 | 10 | (0.646, 0.3), (0.95, 0) |
| `FOTB` | 储存器官分配系数 | 10 | (1, 1), (2, 1) |
| `FRTB` | 根系分配系数 | 10 | (0, 0.5), (0.5, 0.13), (1.2, 0) |
| `FSTB` | 茎秆分配系数 | 10 | (0.646, 0.7), (0.95, 1) |
| `RDRRTB` | 根系相对死亡率 | 10 | (1.5, 0), (1.5001, 0.02), (2, 0.02) |
| `RDRSTB` | 茎秆相对死亡率 | 10 | 同 RDRRTB |
| `RFSETB` | 根/冠降低因子 | 10 | (0, 1), (2, 1) |
| `SLATB` | 比叶面积随 DVS 变化 | 10 | (0, 0.00212), (2, 0.00212) |
| `TMNFTB` | 最低温度影响系数 | 10 | — |
| `TMPFTB` | 霜冻致死温度阈值 | 10 | — |

**数据库取值规则**（在 `fetch_cropdata()` 中）：
1. `crop_parameter_value` → 先取作物默认参数
2. `variety_parameter_value` → 再取特定品种的覆盖值（如果存在则替换）
3. 代码层面转换：`SSA → SSATB[0, SSA, 2.0, SSA]`, `KDIF → KDIFTB[0, 0.6, 2.0, 0.6]`, `EFF → EFFTB[0, 0.45, 40.0, 0.45]`

### `variety_parameter_value` — 品种参数覆盖

与 `crop_parameter_value` 结构完全相同，但增加了 `variety_no`，实现"继承+覆盖"模式。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `crop_no` | INTEGER | **PK** | 作物编号 |
| `variety_no` | INTEGER | **PK** | 品种编号 |
| `parameter_code` | VARCHAR(20) | **PK** | 参数代码 |
| `parameter_xvalue` | NUMERIC(10,5) | NOT NULL | 标量值 |
| `parameter_yvalue` | NUMERIC(10,5) | NULL | 表格 Y 值 |

典型覆盖场景：同一作物（如冬小麦 crop=10）的不同品种有不同的 `TSUM1`、`TSUM2` 积温要求。品种通过 `TSUM1`、`TSUM2` 的细微差异反映发育期早晚。

示例数据（冬小麦不同品种的 TSUM1）：
| crop_no | variety_no | parameter_code | parameter_xvalue |
|---------|------------|----------------|------------------|
| 10 | 2557 | TSUM1 | 31.9°C·d |
| 10 | 2561 | TSUM1 | 307.9°C·d |
| 10 | 2576 | TSUM1 | 289.6°C·d |

### `crop_calendar` — 作物日历（轮作计划）

定义每个网格+作物+年份的种植计划和关键时间节点。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `grid_no` | INTEGER | **PK** | 网格编号 |
| `crop_no` | INTEGER | **PK** | 作物编号 |
| `variety_no` | INTEGER | NOT NULL | 品种编号 |
| `year` | INTEGER | **PK** | 年份 |
| `start_date` | DATE | NOT NULL | 模拟起始日期（可早于播种） |
| `crop_start_type` | VARCHAR(20) | NOT NULL | 起始类型（`sowing` 播种 / `emergence` 出苗） |
| `crop_start_date` | DATE | NOT NULL | 实际播种/出苗日期 |
| `crop_end_type` | VARCHAR(20) | NOT NULL | 结束类型（`maturity` 成熟 / `harvest` 收获 / `earliest` 最早） |
| `crop_end_date` | DATE | NOT NULL | 预期结束日期（`maturity` 时可为任意远） |
| `max_duration` | INTEGER | NOT NULL | 最大生长期（天数） |

**注意**：
- `crop_end_type = 'maturity'` 时，模型运行至作物生理成熟（DVS=2）才停止
- `crop_end_type = 'harvest'` 时，到指定日期强制收获
- 跨日历年作物（如冬小麦秋播夏收）的 `start_date` 可以在前一年

示例：
| grid_no | crop_no | variety_no | year | start_type | crop_start | end_type | max_duration |
|---------|---------|------------|------|-----------|------------|---------|-------------|
| 31031 | 1 | 2542 | 2000 | emergence | 2000-01-01 | maturity | 365 |
| 1 | 3 | 1 | 1965 | **sowing** | 1965-02-24 | harvest | 365 |

---

## 6. 模拟输出

### `sim_results_timeseries` — 逐日模拟结果

每条记录为某网格+作物+年份在特定模拟模式下某一天的模拟状态快照。

| 列名 | 类型 | 约束 | 说明 | 单位 |
|------|------|------|------|------|
| `grid_no` | INTEGER | **PK** | 网格编号 | — |
| `crop_no` | INTEGER | **PK** | 作物编号 | — |
| `year` | INTEGER | **PK** | 年份 | — |
| `day` | DATE | **PK** | 模拟日期 | YYYY-MM-DD |
| `simulation_mode` | VARCHAR(3) | **PK** | 生产模式（`pp`=潜在 / `wlp`=水限） | — |
| `member_id` | INTEGER | **PK** | 集合成员（0 = 确定性模拟） | — |
| `DVS` | NUMERIC(10,5) | NULL | 发育阶段（0=出苗, 1=开花, 2=成熟） | — |
| `LAI` | NUMERIC(10,5) | NULL | 叶面积指数 | m²/m² |
| `TAGP` | NUMERIC(10,5) | NULL | 总地上生物量 | kg/ha |
| `TWSO` | NUMERIC(10,5) | NULL | 储存器官（籽粒/块茎）总干重 | kg/ha |
| `TWLV` | NUMERIC(10,5) | NULL | 叶片总干重 | kg/ha |
| `TWST` | NUMERIC(10,5) | NULL | 茎秆总干重 | kg/ha |
| `TWRT` | NUMERIC(10,5) | NULL | 根系总干重 | kg/ha |
| `TRA` | NUMERIC(10,5) | NULL | 实际蒸腾量 | cm |
| `RD` | NUMERIC(10,5) | NULL | 当前根深 | cm |
| `SM` | NUMERIC(10,5) | NULL | 土壤水分含量 | — |

**复合主键**：`(grid_no, crop_no, year, day, simulation_mode, member_id)`

模拟模式含义：
- `pp` = Potential Production（潜在生产：水分养分充足，仅受辐射和温度限制）
- `wlp` = Water-Limited Production（水限生产：受水分可用性限制）

### `sim_results_summary` — 全季模拟摘要

每条记录为一次完整模拟的全季汇总结果，包含关键日期和最终状态。

| 列名 | 类型 | 约束 | 说明 | 单位 |
|------|------|------|------|------|
| `grid_no` | INTEGER | **PK** | 网格编号 | — |
| `crop_no` | INTEGER | **PK** | 作物编号 | — |
| `year` | INTEGER | **PK** | 年份 | — |
| `simulation_mode` | VARCHAR(3) | **PK** | 生产模式（`pp` / `wlp`） | — |
| `member_id` | INTEGER | **PK** | 集合成员 | — |
| `DVS` | NUMERIC(10,5) | NULL | 最终发育阶段 | — |
| `LAIMAX` | NUMERIC(10,5) | NULL | 全季最大叶面积指数 | m²/m² |
| `TAGP` | NUMERIC(10,5) | NULL | 总地上生物量（终值） | kg/ha |
| `TWSO` | NUMERIC(10,5) | NULL | 籽粒/块茎产量（终值） | kg/ha |
| `TWLV` | NUMERIC(10,5) | NULL | 叶片干重（终值） | kg/ha |
| `TWST` | NUMERIC(10,5) | NULL | 茎秆干重（终值） | kg/ha |
| `TWRT` | NUMERIC(10,5) | NULL | 根系干重（终值） | kg/ha |
| `CTRAT` | NUMERIC(10,5) | NULL | 蒸腾-蒸散比 | — |
| `RD` | NUMERIC(10,5) | NULL | 根深（终值） | cm |
| `DOS` | DATE | NULL | 播种日期 | — |
| `DOE` | DATE | NULL | 出苗日期 | — |
| `DOA` | DATE | NULL | 开花日期 | — |
| `DOM` | DATE | NULL | 成熟日期 | — |
| `DOH` | DATE | NULL | 收获日期 | — |
| `DOV` | DATE | NULL | （附加日期） | — |

**与 `sim_results_timeseries` 的区别**：
- Timeseries 是每日快照，用于过程分析
- Summary 是一次模拟一行，用于多场景对比

### `wofost_unittest_benchmarks` — 单元测试基准数据

结构与 `sim_results_timeseries` 几乎相同，用于回归测试的黄金标准数据集。

| 列名 | 类型 | 与 timeseries 差异 |
|------|------|-------------------|
| 所有列 | 相同 | 完全一致 |
| `SM` | NUMERIC(10,5) | 位置略不同 |

**用途**：`test_wofost72.py` 中的 12 个回归测试将当前运行输出与此表的基准数据逐日逐变量比对，确保模型升级不改性结果。

---

## 7. 工具与任务管理

### `tasklist` — 批量模拟任务队列

用于分布式批处理的任务调度表。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `task_id` | INTEGER | **PK** | 任务 ID |
| `status` | VARCHAR(15) | NOT NULL | 状态（`Pending`, `In progress`, `Finished`, `Error occurred`） |
| `hostname` | VARCHAR(50) | NULL | 执行主机名 |
| `grid_no` | INTEGER | NOT NULL | 网格编号 |
| `crop_no` | INTEGER | NOT NULL | 作物编号 |
| `year` | INTEGER | NOT NULL | 年份 |
| `sim_mode` | VARCHAR(5) | NULL | 模拟模式（`WLP`, `PP`） |
| `randomseed` | INTEGER | NOT NULL | 随机种子 |

---

## 8. 键值对模式详解

PCSE 数据库最突出的设计特点是 **键值对参数存储**，体现在三张表：

```
crop_parameter_value     (crop_no, parameter_code) → xvalue, yvalue
variety_parameter_value  (crop_no, variety_no, parameter_code) → xvalue, yvalue
soil_physical_group      (soil_group_no, parameter_code) → xvalue, yvalue
```

**标量参数**：仅使用 `xvalue`，`yvalue = NULL`
```sql
INSERT INTO crop_parameter_value VALUES(1, 'TDWI', 210, NULL);        -- 初始干物重 210 kg/ha
INSERT INTO crop_parameter_value VALUES(1, 'RDMCR', 125, NULL);       -- 最大根深 125 cm
```

**表格参数**：以 `_NN` 后缀区分行，`xvalue` 为 X 轴（通常 DVS），`yvalue` 为参数值
```sql
-- AMAXTB: 最大CO2同化速率随发育阶段变化 (X=DVS, Y=AMAX kg/ha·h)
INSERT INTO crop_parameter_value VALUES(1, 'AMAXTB_01', 0,    35.83);  -- 出苗时 AMAX=35.83
INSERT INTO crop_parameter_value VALUES(1, 'AMAXTB_02', 1,    35.83);  -- 开花时 AMAX=35.83
INSERT INTO crop_parameter_value VALUES(1, 'AMAXTB_03', 1.3,  35.83);  -- 灌浆期 AMAX=35.83
INSERT INTO crop_parameter_value VALUES(1, 'AMAXTB_04', 2,    4.48);   -- 成熟时 AMAX=4.48
INSERT INTO crop_parameter_value VALUES(1, 'AMAXTB_05', 0,    0);      -- 结尾填充 (0,0)
```

**末尾填充**：多余的 `_NN` 行填 `(0, 0)`（CGMS 固定每表 10 行用于旬输出）。

**默认+覆盖查询逻辑**（伪代码）：
```python
# 1. 从 crop_parameter_value 取默认值
for param in scalar_params:
    cropdata[param] = fetch("crop_parameter_value", crop, param)

# 2. 从 variety_parameter_value 取品种覆盖值
for param in scalar_params:
    if exists("variety_parameter_value", crop, variety, param):
        cropdata[param] = fetch("variety_parameter_value", crop, variety, param)
```

**优势**：
- 添加新作物参数无需 ALTER TABLE，只需 INSERT 新行
- 不同作物可定义不同的参数集
- 品种差异化只需覆盖特定参数

---

## 9. 数据流向

### 启动流程（`start_wofost()`）

```
用户调用 pcse.start_wofost(grid=31031, crop=1, year=2000, mode='wlp')
    │
    ├─ 1. 连接 SQLite 数据库 (~/.pcse/pcse.db)
    │
    ├─ 2. AgroManagementDataProvider
    │       └─ crop_calendar 表 → YAML 格式农艺管理指令
    │          (crop_start_type, crop_end_type, max_duration 等)
    │
    ├─ 3. fetch_sitedata()
    │       └─ site 表 → 水文参数 (WAV, SMLIM, IFUNRN 等)
    │
    ├─ 4. fetch_cropdata()
    │       ├─ crop 表 → 作物名称
    │       ├─ crop_calendar 表 → 品种编号 (variety_no)
    │       ├─ crop_parameter_value 表 → 默认参数 (34 标量 + 12 表格)
    │       └─ variety_parameter_value 表 → 品种覆盖参数
    │
    ├─ 5. fetch_soildata()
    │       ├─ soil_type 表 → 土壤类型编号
    │       ├─ soil_layers 表 → 土层厚度 (单层)
    │       └─ soil_physical_group 表 → 7 个物理参数
    │
    ├─ 6. ParameterProvider(sitedata, soildata, cropdata)
    │       └─ 汇聚为统一参数字典
    │
    ├─ 7. GridWeatherDataProvider(grid=31031)
    │       └─ grid_weather 表 → 逐日气象 (含单位转换 + cache)
    │
    ├─ 8. 实例化模型 (Wofost72_WLP_CWB)
    │
    └─ 返回可运行的模型对象
```

### 输出写入流程

```
模型运行 run_till_terminate()
    │
    ├─ get_output() → 逐日状态列表 (内存)
    │
    └─ get_summary_output() → 全季汇总字典 (内存)
    
输出存储（CGMS 批处理场景）：
    ├─ sim_results_timeseries ← 逐日 INSERT
    └─ sim_results_summary    ← 全季 INSERT
```

---

## 10. PCSE Demo 数据库 vs CGMS 生产数据库

| 特性 | PCSE Demo DB | CGMS 生产 DB |
|------|-------------|-------------|
| 数据库文件 | `~/.pcse/pcse.db` | 中心化服务器 |
| 数据规模 | 3 个网格, 17 种作物, 2 年 | 全欧 10000+ 网格, 数十年 |
| 天气数据 | 完整每日气象要素 | 相同结构 |
| 集合预报 | 50 成员 × 1 年 | 多年集合 |
| 任务管理 | tasklist 表 (手工) | TaskManager (SQLAlchemy) |
| 土壤 | 仅单层土壤 | 支持多层 |
| 构建方式 | `pcse_dump.sql` 自动加载 | 外部 ETL 管道 |
| 用途 | 学习/开发/测试 | 欧盟作物监测业务运行 |

---

## 11. 表关系图

```
┌──────────────┐    ┌──────────────────────┐    ┌─────────────────────────┐
│     grid     │    │     grid_weather      │    │  ensemble_grid_weather  │
│──────────────│    │──────────────────────│    │─────────────────────────│
│ PK grid_no   │───▶│ FK grid_no           │    │ FK grid_no              │
│ latitude     │    │ PK day               │    │ PK day                  │
│ longitude    │    │ TMAX, TMIN, VAP, ... │    │ PK member_id            │
│ altitude     │    │ e0, es0, et0, ...    │    │ rainfall                │
└──────────────┘    └──────────────────────┘    └─────────────────────────┘
        │
        ├──▶ ┌──────────────┐    ┌──────────────────┐    ┌────────────────────────┐
        │    │  soil_type   │    │   soil_layers    │    │  soil_physical_group   │
        │    │──────────────│    │──────────────────│    │────────────────────────│
        │    │ FK grid_no   │───▶│ FK soil_type_no  │    │ FK soil_group_no       │
        │    │ FK soil_type │    │ PK layer_no      │───▶│ PK parameter_code      │
        │    └──────────────┘    │ thickness        │    │ xvalue, yvalue         │
        │                        │ FK soil_group_no │    └────────────────────────┘
        │                        └──────────────────┘
        │
        ├──▶ ┌──────────────┐
        │    │    site      │
        │    │──────────────│
        │    │ FK grid_no   │
        │    │ PK year      │
        │    │ IFUNRN, WAV, │
        │    │ SMLIM, SSMAX │
        │    └──────────────┘
        │
        └──▶ ┌─────────────────────┐    ┌─────────────────────────┐
             │   crop_calendar     │    │          crop           │
             │─────────────────────│    │─────────────────────────│
             │ FK grid_no          │    │ PK crop_no              │
             │ FK crop_no          │───▶│ crop_name               │
             │ PK year             │    │ cropgroup_no            │
             │ FK variety_no       │    │ crop_model              │
             │ start/end_date, ... │    └─────────────────────────┘
             └─────────────────────┘               │
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    ▼                              ▼                              ▼
        ┌──────────────────────┐    ┌──────────────────────────┐    ┌─────────────────────────┐
        │ crop_parameter_value │    │ variety_parameter_value  │    │  sim_results_timeseries │
        │──────────────────────│    │──────────────────────────│    │─────────────────────────│
        │ FK crop_no           │    │ FK crop_no               │    │ FK grid_no              │
        │ PK parameter_code    │    │ FK variety_no            │    │ FK crop_no              │
        │ xvalue, yvalue       │    │ PK parameter_code        │    │ PK year, PK day         │
        └──────────────────────┘    │ xvalue, yvalue           │    │ PK sim_mode, member_id  │
                                    └──────────────────────────┘    │ DVS, LAI, TAGP, TWSO... │
                                                                     └─────────────────────────┘
                                                                                  │
                                                                                  ▼
                                                                     ┌─────────────────────────┐
                                                                     │   sim_results_summary   │
                                                                     │─────────────────────────│
                                                                     │ FK grid_no, FK crop_no  │
                                                                     │ PK year, PK sim_mode    │
                                                                     │ PK member_id            │
                                                                     │ LAIMAX, TAGP, DOS, ...  │
                                                                     └─────────────────────────┘
```

---

## 12. 与硅基一号数据库的对应关系

PCSE 的数据库设计直接启发了硅基一号温室种植数据库。核心映射：

| PCSE 表 | 硅基一号表 | 映射说明 |
|---------|-----------|---------|
| `grid` | `device` | 空间网格 → 具体设备/温室，增加设备状态字段 |
| `grid_weather` | `sensor_readings` + `sensor_hourly` | 单源气象 → 多源传感器（温度/湿度/CO₂/PAR...），增加分钟级精度 |
| `crop` | `crop_type` | 大田作物 → 温室作物（番茄等），增加生长习性、种植方式字段 |
| `crop_calendar` | `growth_cycle` | 一年一季 → 无限生长型，增加定植/打顶/拉秧日期，支持多茬循环 |
| `crop_parameter_value` | `crop_params` | 键值对模式完全继承，参数域从 WOFOST 参数变为 GDD 积温/光合参数 |
| `variety_parameter_value` | `variety_params` | 品种覆盖模式完全继承 |
| `soil_type` + `soil_layers` + `soil_physical_group` | `substrate_type` + `substrate_params` | 土壤变为基质（岩棉/椰糠），参数域完全不同 |
| `site` | `device_config` | 场地水文 → 设备全局配置（控制策略/阈值/调度参数） |
| `sim_results_timeseries` | `sim_output_timeseries` | 逐日输出 → 模型逐日/逐时预测，增加 GDD/补光时长/灌溉量列 |
| `sim_results_summary` | `cycle_summary` | 全季摘要 → 种植茬口汇总，增加产量/品质/资源消耗统计 |
| — | `gdd_tracking` | 新增：积温逐日追踪（硅基一号使用 GDD 法驱动物候） |
| — | `control_actions` + `irrigation_log` + `decision_log` + `alert_log` | 新增：温室特有的控制/决策/告警闭环 |
| — | `knowledge_base` | 新增：农艺经验知识库 |

**核心差异**：
- PCSE 是**离线批处理**（模拟结束写入结果），硅基一号是**在线边云协同**（实时采集 → 在线推理 → 指令下发）
- PCSE 的 `crop_calendar` 是静态计划（播种/收获日期），硅基一号的 `growth_cycle` 是动态生命周期（定植→花期→坐果→打顶→拉秧）
- 硅基一号新增了完整的**控制闭环**表（控制指令 → 执行记录 → 效果反馈）
