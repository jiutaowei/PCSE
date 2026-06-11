# 种植方案生成数据库设计

> 本文档设计一套面向"种植方案生成"的业务数据库。用户录入地块、土壤、气象和品种参数后，系统调用算法生成可落地的种植方案（什么时候种、什么时候浇水施肥、预期产量和风险）。
>
> 数据库建议使用 PostgreSQL 15+。JSONB、GIN 索引和 CHECK 约束可按目标数据库能力等价替换。

---

## 1. 设计思路

### 1.1 输入什么、输出什么

```
输入                              输出（种植方案）
──────────────────────────       ──────────────────────────
地块位置 + 设施类型              播种/定植日期 + 预计采收日期
土壤剖面（分层属性）      →      株行距 + 目标密度
历史气象数据                     灌溉计划（哪天浇、浇多少）
作物、品种参数（积温、耐温等）      施肥计划（哪天施、用什么肥）
用户目标（高产/稳产/省水）       条件触发规则（土壤干了就浇）
                                 预期产量、耗水、风险评分
                                 为什么推荐这个方案的说明
```

### 1.2 一份方案就是一条 plan 记录

不做多茬嵌套。一块地种一茬就是一条 `plan`，多茬就多条记录，简单直接。

| 方案里包含什么 | 存在哪 |
|---|---|
| 在哪块地、种什么品种、什么时候种收、密度多少 | `plan` |
| 灌溉、施肥、巡田等按日期安排的任务 | `plan_task` |
| 按条件触发的规则（土壤干了才浇水） | `plan_trigger` |
| 预期产量、耗水、风险评分、推荐理由 | `plan_result` |

### 1.3 参数和指标统一管理

不同作物、品种需要的参数不同（比如积温、耐温范围、目标密度），通过以下表统一管理：

| 表 | 干什么用 |
|---|---|
| `parameter_dict` | 参数字典——定义"有哪些参数、单位是什么、合理范围多少" |
| `crop_param_set` | 品种参数集——"某品种的一套参数版本" |
| `crop_param_value` | 参数值——"这套参数里每个参数具体填了什么数" |
| `response_curve` / `response_curve_point` | 响应曲线——"温度对发育速率的影响"这类非线性关系 |

### 1.4 四层架构

```text
基础资料层（作物 / 品种 / 地块 / 土壤 / 气象 / 参数 / 指标）
    ↓
方案输出层（方案 / 任务 / 触发规则 / 预期结果）
    ↓
预测中间层（预测运行 / 逐日指标）
    ↓
执行复盘层（实际操作 / 观测数据）
```

层间单向依赖。比如地块数据不依赖种植方案，执行记录不影响基础资料。

---

## 2. 表清单

全库 **25 张表 + 4 个视图**，按业务领域分组。

### 2.1 字典与配置（5 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 1 | `algorithm` | 算法注册表——系统支持哪些预测/生成算法 |
| 2 | `parameter_dict` | 参数字典——所有参数的定义（名称、单位、范围） |
| 3 | `metric_dict` | 指标字典——所有输出指标的定义（产量、耗水、风险等） |
| 4 | `response_curve` | 响应曲线——曲线名称和坐标轴含义 |
| 5 | `response_curve_point` | 响应曲线点——曲线上的每个 X/Y 坐标 |

### 2.2 作物与品种（4 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 6 | `crop` | 作物表——系统支持种哪些作物 |
| 7 | `crop_variety` | 品种表——每个作物下有哪些品种 |
| 8 | `crop_param_set` | 品种参数集——某品种的一套参数（可有多个版本） |
| 9 | `crop_param_value` | 参数值——参数集里每个参数的具体数值 |

### 2.3 土壤（3 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 10 | `soil_type` | 土壤类型模板——常见土层的通用属性 |
| 11 | `soil_profile` | 土壤剖面——某个地块的土壤整体描述 |
| 12 | `soil_profile_layer` | 剖面层——剖面的每一层详细参数 |

### 2.4 地块（2 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 13 | `site` | 地块表——种植位置、设施类型、面积 |
| 14 | `site_condition` | 地块条件——某地块在某年的土壤初始状态 |

### 2.5 气象（2 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 15 | `weather_source` | 气象来源——数据从哪来（传感器、API、人工录入） |
| 16 | `weather_record` | 逐日气象——每天的温湿度、降水、辐射等 |

### 2.6 种植方案（4 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 17 | `plan` | 种植方案——一茬作物的完整种植计划 |
| 18 | `plan_task` | 农事任务——方案里的计划动作（灌溉、施肥、采收等） |
| 19 | `plan_trigger` | 触发规则——按条件触发的操作（如土壤干了就浇水） |
| 20 | `plan_result` | 方案结果——预期产量、耗水、风险评分和推荐理由 |

### 2.7 预测（2 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 21 | `prediction_run` | 预测运行——算法跑了一次的上下文和状态 |
| 22 | `prediction_daily` | 预测日指标——每天的预测数值（发育阶段、土壤水分等） |

### 2.8 执行复盘（3 张）

| # | 表名 | 一句话说明 |
|---|---|---|
| 23 | `plan_operation` | 操作记录——用户实际做了什么（可能和计划有偏差） |
| 24 | `obs_summary` | 观测汇总——一茬的实测结果（实收产量、病害率等） |
| 25 | `obs_timeseries` | 观测时序——每天的实测数据（土壤水分、长势评分等） |

### 2.9 视图（4 个）

| 视图 | 一句话说明 |
|---|---|
| `v_plan_overview` | 方案概览——方案 + 地块 + 作物 + 预期结果 |
| `v_plan_tasks` | 任务时间线——方案的任务按日期排列 |
| `v_prediction_daily` | 预测日指标——关键日指标宽表 |
| `v_obs_vs_plan` | 实测 vs 预测——对比偏差 |

---

## 3. 表结构详细定义

### 3.1 字典与配置

#### `algorithm` — 算法注册表

登记系统支持哪些预测或生成算法。算法可以是规则引擎、机器学习模型、作物生长模型或专家系统。表里只存基本信息，不存运行结果。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `algo_code` | TEXT | NOT NULL, UNIQUE | 算法代码，如 `rule_v1`、`ml_yield_v2` |
| `algo_name` | TEXT | NOT NULL | 算法名称 |
| `algo_type` | TEXT | NOT NULL, CHECK IN `rule/ml/statistical/crop_model/expert/hybrid/manual` | 算法类型 |
| `algo_version` | TEXT | NOT NULL | 版本号 |
| `supported_crops` | JSONB | 可空 | 支持的作物代码列表 |
| `supported_facilities` | JSONB | 可空 | 支持的设施类型列表 |
| `input_schema` | JSONB | 可空 | 输入数据要求 |
| `output_schema` | JSONB | 可空 | 输出指标说明 |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| `description` | TEXT | 可空 | 描述 |

| 约束/索引 | 定义 |
|---|---|
| 索引 | `idx_algorithm_type(algo_type, algo_version)` |

---

#### `parameter_dict` — 参数字典

全库的"参数说明书"。所有参数在录入数值之前，先在这里登记——叫什么、单位是什么、合理范围多少。填参数值时系统自动校验是否在范围内。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `code` | TEXT | NOT NULL, UNIQUE | 参数代码，如 `base_temp`、`target_density` |
| `scope` | TEXT | NOT NULL, CHECK IN `crop/soil/site/weather/management/model` | 属于哪个领域 |
| `param_group` | TEXT | 可空 | 参数分组，如 `phenology`（物候）、`root`（根系） |
| `value_kind` | TEXT | NOT NULL, CHECK IN `scalar/curve/array/object/text/boolean` | 值的类型 |
| `unit` | TEXT | 可空 | 单位 |
| `description` | TEXT | 可空 | 参数说明 |
| `range_min` | DOUBLE PRECISION | 可空 | 最小值 |
| `range_max` | DOUBLE PRECISION | 可空 | 最大值 |
| `allowed_values` | JSONB | 可空 | 枚举值列表（值类型为 text 时使用） |
| `default_value` | JSONB | 可空 | 默认值 |
| `required_for_algorithms` | JSONB | 可空 | 哪些算法要求必须填这个参数 |
| `source_note` | TEXT | 可空 | 来源说明 |

| 约束/索引 | 定义 |
|---|---|
| 范围检查 | `range_min IS NULL OR range_max IS NULL OR range_min <= range_max` |
| 索引 | `idx_parameter_dict_scope(scope, param_group)` |

---

#### `metric_dict` — 指标字典

全库的"指标说明书"。定义系统会输出哪些指标（产量、耗水、风险评分等）、类型和单位。不同算法可以输出不同指标，但编码统一在这里管理。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `algorithm_id` | BIGINT | FK → `algorithm.id` | 适用于哪个算法；空 = 通用指标 |
| `metric_code` | TEXT | NOT NULL | 指标代码，如 `expected_yield`、`water_use` |
| `metric_name` | TEXT | NOT NULL | 指标名称 |
| `metric_kind` | TEXT | NOT NULL, CHECK IN `daily/summary/final/score/risk` | 指标类型 |
| `unit` | TEXT | 可空 | 单位 |
| `description` | TEXT | 可空 | 说明 |
| `is_yield_metric` | BOOLEAN | NOT NULL, DEFAULT false | 是否为产量相关指标 |
| `is_key_metric` | BOOLEAN | NOT NULL, DEFAULT false | 是否为重点展示指标 |
| `display_order` | INT | 可空 | 展示排序 |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(algorithm_id, metric_code, metric_kind)` |

---

#### `response_curve` — 响应曲线

存放可复用的非线性关系曲线。比如"温度对发育速率的影响"不是简单线性——0°C 不发育，25°C 最快，35°C 又降下来。这种关系用一条曲线（多个 X/Y 点）描述。

这张表只存曲线的名称和坐标轴含义，具体点位在 `response_curve_point` 中。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `curve_code` | TEXT | NOT NULL, UNIQUE | 曲线代码 |
| `curve_name` | TEXT | NOT NULL | 曲线名称 |
| `x_variable` | TEXT | 可空 | X 轴变量名 |
| `y_variable` | TEXT | 可空 | Y 轴变量名 |
| `x_unit` | TEXT | 可空 | X 轴单位 |
| `y_unit` | TEXT | 可空 | Y 轴单位 |
| `source` | TEXT | 可空 | 数据来源 |
| `description` | TEXT | 可空 | 描述 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

---

#### `response_curve_point` — 响应曲线点

曲线上的每个坐标点。比如温度-发育速率曲线的 (0°C, 0)、(25°C, 1.0)、(35°C, 0.3)。按 `point_no` 排序还原整条曲线。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `curve_id` | BIGINT | PK, FK → `response_curve.id`, ON DELETE CASCADE | 所属曲线 |
| `point_no` | INT | PK | 点序号 |
| `x_value` | DOUBLE PRECISION | NOT NULL | X 值 |
| `y_value` | DOUBLE PRECISION | NOT NULL | Y 值 |

| 约束/索引 | 定义 |
|---|---|
| 主键 | `(curve_id, point_no)` |
| 唯一约束 | `(curve_id, x_value)` — 同一曲线不能有重复 X 值 |

---

### 3.2 作物与品种

#### `crop` — 作物表

系统支持种植哪些作物，比如小麦、玉米、番茄。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `crop_code` | TEXT | NOT NULL, UNIQUE | 作物代码，如 `wheat`、`maize`、`tomato` |
| `crop_name` | TEXT | NOT NULL | 作物名称 |
| `crop_name_en` | TEXT | 可空 | 英文名 |
| `scientific_name` | TEXT | 可空 | 学名 |
| `crop_group` | TEXT | 可空 | 作物大类：cereal（谷物）、vegetable（蔬菜）、fruit（水果）、grass（牧草） |
| `typical_growth_days` | INT | 可空 | 常见生育期天数（没有品种参数时的粗略估计） |
| `description` | TEXT | 可空 | 描述 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

---

#### `crop_variety` — 品种表

每个作物下的具体品种。比如番茄下的"千禧"、"京丹 5 号"。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `crop_id` | BIGINT | NOT NULL, FK → `crop.id` | 所属作物 |
| `variety_code` | TEXT | NOT NULL | 品种代码 |
| `variety_name` | TEXT | NOT NULL | 品种名称 |
| `variety_name_en` | TEXT | 可空 | 英文名 |
| `maturity_group` | TEXT | 可空 | 熟性：early（早熟）/medium（中熟）/late（晚熟） |
| `suitable_season` | TEXT | 可空 | 适宜季节 |
| `suitable_facility` | TEXT | 可空 | 适宜设施类型 |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| `description` | TEXT | 可空 | 描述 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(crop_id, variety_code)` |

---

#### `crop_param_set` — 品种参数集

某个品种的一套参数版本。同一个品种可能有"官方推荐参数"、"本地标定参数"等多个版本。`is_default` 标记默认用哪套，`parent_id` 记录派生关系。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `variety_id` | BIGINT | NOT NULL, FK → `crop_variety.id` | 所属品种 |
| `algorithm_id` | BIGINT | FK → `algorithm.id` | 适用于哪个算法；空 = 通用参数集 |
| `version_label` | TEXT | NOT NULL | 版本号，如 `v1.0`、`calibrated_2026` |
| `source_type` | TEXT | NOT NULL, CHECK IN `manual/calibrated/paper/experiment/imported/generated` | 参数来源 |
| `source_note` | TEXT | 可空 | 来源说明 |
| `checksum` | TEXT | 可空 | 参数校验和（防止意外修改） |
| `parent_id` | BIGINT | FK → `crop_param_set.id` | 从哪套参数派生来的 |
| `is_default` | BOOLEAN | NOT NULL, DEFAULT false | 是否为默认参数集 |
| `notes` | TEXT | 可空 | 备注 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(variety_id, algorithm_id, version_label)` |
| 索引 | `idx_crop_param_set_lookup(variety_id, algorithm_id)` |

---

#### `crop_param_value` — 参数值

参数集里每个参数的具体数值。比如 `base_temp` = 10°C，`target_density` = 3500 株/亩。值可以是标量、文本、布尔、JSON 对象，或者引用一条响应曲线。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `param_set_id` | BIGINT | NOT NULL, FK → `crop_param_set.id`, ON DELETE CASCADE | 所属参数集 |
| `parameter_code` | TEXT | NOT NULL, FK → `parameter_dict.code` | 参数代码 |
| `value_kind` | TEXT | NOT NULL, CHECK IN `scalar/curve/array/object/text/boolean` | 值类型 |
| `value_scalar` | DOUBLE PRECISION | 可空 | 数值（value_kind = scalar 时填） |
| `value_text` | TEXT | 可空 | 文本值（value_kind = text 时填） |
| `value_bool` | BOOLEAN | 可空 | 布尔值（value_kind = boolean 时填） |
| `value_json` | JSONB | 可空 | JSON 值（value_kind = array/object 时填） |
| `curve_id` | BIGINT | FK → `response_curve.id` | 引用响应曲线（value_kind = curve 时填） |
| `unit` | TEXT | 可空 | 单位 |
| `source_note` | TEXT | 可空 | 来源说明 |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(param_set_id, parameter_code)` — 同一参数集内不重复 |

---

### 3.3 土壤

#### `soil_type` — 土壤类型模板

预定义的常见土壤类型，如"砂壤土"、"黏壤土"。每种类型有典型的容重、持水量、有机质等属性，多个地块可共享。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `type_code` | TEXT | NOT NULL, UNIQUE | 类型代码 |
| `type_name` | TEXT | NOT NULL | 类型名称 |
| `texture` | TEXT | 可空 | 质地（砂土/壤土/黏土等） |
| `bulk_density` | DOUBLE PRECISION | 可空 | 容重 (g/cm³) |
| `field_capacity` | DOUBLE PRECISION | 可空 | 田间持水量 (m³/m³) |
| `wilting_point` | DOUBLE PRECISION | 可空 | 凋萎点含水量 (m³/m³) |
| `saturation_water` | DOUBLE PRECISION | 可空 | 饱和含水量 (m³/m³) |
| `hydraulic_conductivity` | DOUBLE PRECISION | 可空 | 导水率 (cm/day) |
| `soil_ph` | DOUBLE PRECISION | 可空 | 土壤 pH |
| `organic_matter` | DOUBLE PRECISION | 可空 | 有机质含量 (g/kg) |
| `description` | TEXT | 可空 | 描述 |

---

#### `soil_profile` — 土壤剖面

某个地块的土壤整体描述。可以是简单的单层剖面，也可以是多层剖面（分 0-20cm、20-40cm 等层）。土壤剖面决定根系能扎多深、能蓄多少水，直接影响灌溉和施肥建议。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `profile_code` | TEXT | NOT NULL, UNIQUE | 剖面代码 |
| `profile_name` | TEXT | NOT NULL | 剖面名称 |
| `profile_type` | TEXT | NOT NULL, CHECK IN `single_layer/multi_layer` | 单层/多层 |
| `total_depth_cm` | DOUBLE PRECISION | 可空 | 总深度 (cm) |
| `root_depth_cm` | DOUBLE PRECISION | 可空 | 根系可利用深度 (cm) |
| `field_capacity` | DOUBLE PRECISION | 可空 | 单层模式：田间持水量 |
| `wilting_point` | DOUBLE PRECISION | 可空 | 单层模式：凋萎点 |
| `saturation_water` | DOUBLE PRECISION | 可空 | 单层模式：饱和含水量 |
| `infiltration_rate` | DOUBLE PRECISION | 可空 | 入渗速率 (cm/day) |
| `drainage_rate` | DOUBLE PRECISION | 可空 | 排水速率 (cm/day) |
| `groundwater` | JSONB | 可空 | 地下水信息（深度、水质等） |
| `description` | TEXT | 可空 | 描述 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

---

#### `soil_profile_layer` — 剖面层

多层剖面的每一层详细参数。`soil_type_id` 引用模板获取默认属性，本表字段可覆盖模板值。`parameters` 存放额外数据（盐分、EC、速效氮磷钾）。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `profile_id` | BIGINT | NOT NULL, FK → `soil_profile.id`, ON DELETE CASCADE | 所属剖面 |
| `layer_no` | INT | NOT NULL | 层号（从上往下） |
| `soil_type_id` | BIGINT | FK → `soil_type.id` | 引用土壤类型模板 |
| `depth_top_cm` | DOUBLE PRECISION | 可空 | 层顶深度 (cm) |
| `depth_bottom_cm` | DOUBLE PRECISION | 可空 | 层底深度 (cm) |
| `thickness_cm` | DOUBLE PRECISION | NOT NULL, CHECK > 0 | 层厚 (cm) |
| `bulk_density` | DOUBLE PRECISION | 可空 | 容重 (g/cm³) |
| `soil_ph` | DOUBLE PRECISION | 可空 | 土壤 pH |
| `organic_matter` | DOUBLE PRECISION | 可空 | 有机质含量 (g/kg) |
| `parameters` | JSONB | 可空 | 额外参数（盐分、EC、速效养分等） |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(profile_id, layer_no)` |
| 深度检查 | `depth_bottom_cm IS NULL OR depth_top_cm IS NULL OR depth_bottom_cm > depth_top_cm` |

---

### 3.4 地块

#### `site` — 地块

种植位置的基本信息。`facility_type`（露地/温室）对方案影响很大——灌溉方式、病害风险、任务安排都不同。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `site_code` | TEXT | NOT NULL, UNIQUE | 地块代码 |
| `site_name` | TEXT | NOT NULL | 地块名称 |
| `latitude` | DOUBLE PRECISION | NOT NULL, CHECK -90 到 90 | 纬度 |
| `longitude` | DOUBLE PRECISION | NOT NULL, CHECK -180 到 180 | 经度 |
| `elevation_m` | DOUBLE PRECISION | NOT NULL, CHECK -300 到 6000 | 海拔 (m) |
| `region` | TEXT | 可空 | 所属区域 |
| `facility_type` | TEXT | CHECK IN `open_field/greenhouse/growth_chamber/container/other` | 设施类型 |
| `area_m2` | DOUBLE PRECISION | 可空 | 面积 (m²) |
| `timezone` | TEXT | DEFAULT `Asia/Shanghai` | 时区 |
| `description` | TEXT | 可空 | 描述 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

---

#### `site_condition` — 地块条件

某个地块在某年的初始状态。地块位置不变，但土壤水分、养分、前茬残留每年不同，需按年/按季记录。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `site_id` | BIGINT | NOT NULL, FK → `site.id` | 所属地块 |
| `soil_profile_id` | BIGINT | NOT NULL, FK → `soil_profile.id` | 使用哪个土壤剖面 |
| `algorithm_id` | BIGINT | FK → `algorithm.id` | 适用于哪个算法；空 = 通用 |
| `condition_year` | INT | 可空 | 年份 |
| `initial_conditions` | JSONB | NOT NULL | 初始条件（见下方示例） |
| `is_default` | BOOLEAN | NOT NULL, DEFAULT false | 是否为默认条件 |
| `valid_from` | DATE | 可空 | 有效起始日期 |
| `valid_to` | DATE | 可空 | 有效截止日期 |
| `notes` | TEXT | 可空 | 备注 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(site_id, soil_profile_id, algorithm_id, condition_year)` |
| 有效期检查 | `valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from` |

**`initial_conditions` JSON 示例**：

```json
{
  "water": {
    "initial_soil_moisture": [0.32, 0.34, 0.35],
    "water_storage_zone_cm": 50.0,
    "surface_storage_cm": 0.0
  },
  "nitrogen": {
    "nh4_kg_ha_layer": [10.5, 8.2, 5.1],
    "no3_kg_ha_layer": [25.0, 18.0, 12.0],
    "total_n_available_kg_ha": 80.0
  },
  "rooting": {
    "initial_root_depth_cm": 10.0,
    "max_root_depth_cm": 120.0
  },
  "previous_crop": {
    "crop": "wheat",
    "residue_kg_ha": 4500,
    "residue_cn_ratio": 80
  },
  "salinity": {
    "ec_ds_m_layer": [1.2, 1.5, 1.8]
  }
}
```

数组长度应与土壤剖面的层数一致。

---

### 3.5 气象

#### `weather_source` — 气象来源

记录气象数据从哪里来。同一地块可能同时有传感器实测和天气预报等多套数据。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `source_code` | TEXT | NOT NULL, UNIQUE | 来源代码 |
| `source_type` | TEXT | NOT NULL, CHECK IN `sensor/api/csv/excel/manual/forecast/nasa_power/open_meteo/custom` | 来源类型 |
| `provider_name` | TEXT | 可空 | 数据提供方名称 |
| `description` | TEXT | 可空 | 描述 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

---

#### `weather_record` — 逐日气象

每天的气象数据，是生成播期、灌溉计划、病害预警和产量预测的基础。`day` 为地块所在时区的民用日。`quality_flag` 标记数据质量。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `site_id` | BIGINT | NOT NULL, FK → `site.id` | 地块 |
| `source_id` | BIGINT | NOT NULL, FK → `weather_source.id` | 气象来源 |
| `day` | DATE | NOT NULL | 日期 |
| `tmin_c` | DOUBLE PRECISION | NOT NULL, CHECK -50 到 60 | 最低温 (°C) |
| `tmax_c` | DOUBLE PRECISION | NOT NULL, CHECK -50 到 60 | 最高温 (°C) |
| `temp_avg_c` | DOUBLE PRECISION | 可空 | 平均温 (°C) |
| `solar_radiation_mj` | DOUBLE PRECISION | 可空 | 日总辐射 (MJ/m²) |
| `relative_humidity` | DOUBLE PRECISION | 可空, CHECK 0-100 | 相对湿度 (%) |
| `vapour_pressure_hpa` | DOUBLE PRECISION | 可空 | 水汽压 (hPa) |
| `rain_mm` | DOUBLE PRECISION | NOT NULL, DEFAULT 0 | 降水量 (mm) |
| `wind_m_s` | DOUBLE PRECISION | 可空 | 风速 (m/s) |
| `et0_mm` | DOUBLE PRECISION | 可空 | 参考蒸散量 (mm) |
| `co2_ppm` | DOUBLE PRECISION | 可空 | 大气 CO₂ 浓度 (ppm) |
| `quality_flag` | TEXT | DEFAULT `ok` | 数据质量：ok/missing/interpolated/anomaly |
| `raw_payload` | JSONB | 可空 | 原始数据（便于追溯） |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(site_id, source_id, day)` |
| 温度检查 | `tmax_c >= tmin_c` |
| 索引 | `idx_weather_record_site_day(site_id, day)` |

---

### 3.6 种植方案

#### `plan` — 种植方案

核心表。一份方案 = 一块地 + 一茬作物 + 从种到收的完整计划。方案有生命周期：草稿 → 已生成 → 已评估 → 已批准 → 执行中 → 已完成 → 已归档。系统可生成多个候选方案，通过 `plan_result` 的评分帮用户选择。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `plan_code` | TEXT | NOT NULL, UNIQUE | 方案代码 |
| `plan_name` | TEXT | NOT NULL | 方案名称 |
| `plan_status` | TEXT | NOT NULL, DEFAULT `draft`, CHECK IN `draft/generated/evaluated/approved/active/completed/archived` | 方案状态 |
| `site_id` | BIGINT | NOT NULL, FK → `site.id` | 地块 |
| `algorithm_id` | BIGINT | FK → `algorithm.id` | 使用的算法 |
| `weather_source_id` | BIGINT | NOT NULL, FK → `weather_source.id` | 气象数据来源 |
| `site_condition_id` | BIGINT | NOT NULL, FK → `site_condition.id` | 地块初始条件 |
| `crop_id` | BIGINT | NOT NULL, FK → `crop.id` | 作物 |
| `variety_id` | BIGINT | NOT NULL, FK → `crop_variety.id` | 品种 |
| `param_set_id` | BIGINT | FK → `crop_param_set.id` | 使用的品种参数集 |
| `crop_start_date` | DATE | NOT NULL | 播种/定植日期 |
| `crop_start_type` | TEXT | NOT NULL, CHECK IN `sowing/transplanting/emergence/regrowth` | 开始方式 |
| `expected_harvest_date` | DATE | 可空 | 预计采收日期 |
| `target_population` | DOUBLE PRECISION | 可空 | 目标密度 (株/m²) |
| `row_spacing_cm` | DOUBLE PRECISION | 可空 | 行距 (cm) |
| `plant_spacing_cm` | DOUBLE PRECISION | 可空 | 株距 (cm) |
| `start_date` | DATE | NOT NULL | 方案开始日期 |
| `end_date` | DATE | 可空 | 方案结束日期 |
| `objective` | TEXT | 可空 | 优化目标，如 maximize_yield / minimize_water / balance |
| `generation_context` | JSONB | 可空 | 生成上下文（算法运行时的额外参数） |
| `summary` | TEXT | 可空 | 方案摘要 |
| `created_by` | TEXT | 可空 | 创建人 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 更新时间 |

| 约束/索引 | 定义 |
|---|---|
| 日期检查 | `end_date IS NULL OR end_date >= start_date` |
| 采收日期 | `expected_harvest_date IS NULL OR expected_harvest_date >= crop_start_date` |
| 索引 | `idx_plan_site_date(site_id, start_date, end_date)` |

---

#### `plan_task` — 农事任务

方案里的计划动作，如灌溉、施肥、植保、采收等。系统生成后直接作为用户的任务日程，带标题、详细说明、预期效果和风险提示。用户执行后在 `plan_operation` 中记录实际操作。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `plan_id` | BIGINT | NOT NULL, FK → `plan.id`, ON DELETE CASCADE | 所属方案 |
| `task_date` | DATE | NOT NULL | 计划日期 |
| `task_type` | TEXT | NOT NULL, CHECK IN `sowing/transplanting/irrigate/fertilize/spray/prune/pollinate/thin/monitor/sample_soil/harvest/custom` | 任务类型 |
| `task_title` | TEXT | NOT NULL | 任务标题（用户可读） |
| `task_detail` | TEXT | NOT NULL | 任务详细说明 |
| `trigger_type` | TEXT | NOT NULL, CHECK IN `date/condition/manual/monitoring` | 触发方式 |
| `trigger_expr` | JSONB | 可空 | 触发表达式（condition 类型时使用） |
| `payload` | JSONB | NOT NULL | 任务参数（水量、肥料名称、用量等） |
| `expected_effect` | TEXT | 可空 | 预期效果 |
| `risk_note` | TEXT | 可空 | 风险提示 |
| `source` | TEXT | NOT NULL, DEFAULT `generated`, CHECK IN `manual/generated/prediction` | 来源 |
| `status` | TEXT | NOT NULL, DEFAULT `planned`, CHECK IN `planned/done/skipped/cancelled` | 状态 |
| `safety_rules` | JSONB | 可空 | 安全规则 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

| 约束/索引 | 定义 |
|---|---|
| 索引 | `idx_plan_task_date(plan_id, task_date)` |
| GIN 索引 | `idx_plan_task_payload(payload)` |

**常见任务类型的 payload 格式**：

| task_type | payload 建议字段 | 说明 |
|---|---|---|
| `irrigate` | `amount_mm`, `efficiency`, `method` | 灌溉。method: drip/sprinkler/flood |
| `fertilize` | `product_name`, `nutrient`, `amount_kg_ha`, `method` | 施肥 |
| `spray` | `product_name`, `dose`, `target`, `preharvest_interval_days` | 喷药 |
| `monitor` | `items`, `method`, `warning_threshold` | 巡田 |
| `sample_soil` | `depth_cm`, `items`, `lab_required` | 土壤采样 |
| `harvest` | `target_maturity`, `quality_standard` | 采收 |

---

#### `plan_trigger` — 触发规则

条件触发型规则。比如"当 0-20cm 土壤含水量低于 60% 时灌溉 12mm"。和固定日期的 `plan_task` 不同，触发规则在执行期间根据实际气象或传感器数据动态判断是否执行。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `plan_id` | BIGINT | NOT NULL, FK → `plan.id`, ON DELETE CASCADE | 所属方案 |
| `trigger_type` | TEXT | NOT NULL, CHECK IN `irrigate/fertilize/spray/monitor/sample_soil/harvest/custom` | 触发后执行的动作类型 |
| `condition_metric` | TEXT | NOT NULL | 监控指标，如 `soil_moisture`、`temperature`、`gdd`、`disease_risk` |
| `operator` | TEXT | NOT NULL, CHECK IN `lt/lte/gt/gte/eq/between` | 判断条件 |
| `threshold_value` | DOUBLE PRECISION | 可空 | 阈值 |
| `threshold_json` | JSONB | 可空 | 复杂阈值（区间或多条件） |
| `comment` | TEXT | 可空 | 说明 |
| `payload` | JSONB | NOT NULL | 触发后的动作参数 |
| `max_trigger_count` | INT | DEFAULT 1 | 最多触发几次 |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |

| 约束/索引 | 定义 |
|---|---|
| 索引 | `idx_plan_trigger_metric(condition_metric, threshold_value)` |

**常用触发指标**：

| 指标代码 | 含义 | 单位 |
|---|---|---|
| `soil_moisture` | 土壤含水量 | m³/m³ |
| `temperature` | 气温 | °C |
| `gdd` | 累积积温 | °C·day |
| `dvs` | 发育阶段指数 | — (0=出苗, 1=开花, 2=成熟) |
| `lai` | 叶面积指数 | m²/m² |
| `disease_risk` | 病害风险指数 | — |
| `rainfall_3day` | 三日累计降水 | mm |

---

#### `plan_result` — 方案结果

方案的预期产出和评分。固定字段存关键指标方便直接查询排序，`score_detail` 存细分评分细节，`reason_summary` 存推荐理由。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `plan_id` | BIGINT | NOT NULL, UNIQUE, FK → `plan.id`, ON DELETE CASCADE | 所属方案（一对一） |
| `prediction_run_id` | BIGINT | FK → `prediction_run.id` | 基于哪次预测运行 |
| `rank_no` | INT | 可空 | 排名（多方案对比时使用） |
| `score` | DOUBLE PRECISION | CHECK 0-100 | 综合评分 |
| `expected_yield` | DOUBLE PRECISION | 可空 | 预期产量 |
| `yield_unit` | TEXT | 可空 | 产量单位（如 kg/ha、kg/亩） |
| `expected_water_use` | DOUBLE PRECISION | 可空 | 预期耗水 |
| `expected_fertilizer_use` | DOUBLE PRECISION | 可空 | 预期用肥量 |
| `expected_cost` | DOUBLE PRECISION | 可空 | 预期成本 |
| `expected_profit` | DOUBLE PRECISION | 可空 | 预期收益 |
| `risk_level` | TEXT | CHECK IN `low/medium/high/critical` | 风险等级 |
| `yield_score` | DOUBLE PRECISION | 可空 | 产量分项评分 |
| `water_score` | DOUBLE PRECISION | 可空 | 水分效率评分 |
| `cost_score` | DOUBLE PRECISION | 可空 | 成本评分 |
| `risk_score` | DOUBLE PRECISION | 可空 | 风险评分 |
| `stability_score` | DOUBLE PRECISION | 可空 | 稳定性评分 |
| `score_detail` | JSONB | 可空 | 评分详情 |
| `reason_summary` | TEXT | 可空 | 推荐理由摘要 |
| `risk_summary` | TEXT | 可空 | 风险提示 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

---

### 3.7 预测

#### `prediction_run` — 预测运行

算法跑了一次的完整记录——用了什么算法和参数、什么气象窗口、成功还是失败。`batch_label` 用于把多次运行归为一组对比（如"品种 A vs 品种 B"）。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `plan_id` | BIGINT | NOT NULL, FK → `plan.id` | 所属方案 |
| `run_code` | TEXT | NOT NULL, UNIQUE | 运行代码 |
| `run_name` | TEXT | 可空 | 运行名称 |
| `batch_label` | TEXT | 可空 | 批次标签（同一批次对比的多个运行用相同的 label） |
| `run_status` | TEXT | NOT NULL, DEFAULT `pending`, CHECK IN `pending/running/succeeded/failed/cancelled` | 运行状态 |
| `algorithm_id` | BIGINT | FK → `algorithm.id` | 使用的算法 |
| `parameter_overrides` | JSONB | 可空 | 本次运行覆盖的参数 |
| `weather_start_date` | DATE | 可空 | 气象数据起始日期 |
| `weather_end_date` | DATE | 可空 | 气象数据截止日期 |
| `weather_year_override` | INT | 可空 | 替换气象年份（用历史年份模拟） |
| `code_version` | TEXT | 可空 | 代码版本号 |
| `random_seed` | BIGINT | 可空 | 随机种子 |
| `started_at` | TIMESTAMPTZ | 可空 | 开始时间 |
| `finished_at` | TIMESTAMPTZ | 可空 | 结束时间 |
| `error_message` | TEXT | 可空 | 错误信息 |
| `log_path` | TEXT | 可空 | 日志路径 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

| 约束/索引 | 定义 |
|---|---|
| 时间检查 | `finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at` |
| 索引 | `idx_prediction_run_status(plan_id, run_status)` |

---

#### `prediction_daily` — 预测日指标

每天的预测数值，如发育阶段、土壤水分、叶面积指数等。采用"长表"结构（每行一个指标），新增指标不须改表结构，在 `metric_dict` 登记即可。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `run_id` | BIGINT | PK, FK → `prediction_run.id`, ON DELETE CASCADE | 预测运行 ID |
| `day` | DATE | PK | 日期 |
| `metric_code` | TEXT | PK | 指标代码 |
| `value` | DOUBLE PRECISION | 可空 | 数值 |
| `value_json` | JSONB | 可空 | 非标量值（如分层数据） |

| 约束/索引 | 定义 |
|---|---|
| 主键 | `(run_id, day, metric_code)` |
| 值互斥 | `value` 和 `value_json` 只填一个 |

---

### 3.8 执行复盘

#### `plan_operation` — 操作记录

用户实际做了什么。计划说"今天浇水 12mm"，实际可能只浇了 8mm 或推迟了两天——记在这里。复盘时和 `plan_task` 对比，分析偏差对产量和风险的影响。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `plan_id` | BIGINT | NOT NULL, FK → `plan.id` | 所属方案 |
| `plan_task_id` | BIGINT | FK → `plan_task.id` | 对应的计划任务 |
| `operation_date` | DATE | NOT NULL | 实际操作日期 |
| `operation_type` | TEXT | NOT NULL | 操作类型 |
| `actual_params` | JSONB | NOT NULL | 实际操作参数 |
| `deviation_reason` | TEXT | 可空 | 与计划的偏差原因 |
| `executed_by` | TEXT | 可空 | 执行人 |
| `verified_by` | TEXT | 可空 | 验证人 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

| 约束/索引 | 定义 |
|---|---|
| 索引 | `idx_plan_operation_date(plan_id, operation_date)` |

---

#### `obs_summary` — 观测汇总

一个方案的实测汇总数据，如实收产量、商品果率、平均单果重、病害发生率。对复盘非常重要。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | BIGSERIAL | PK | 主键 |
| `plan_id` | BIGINT | NOT NULL, FK → `plan.id`, ON DELETE CASCADE | 所属方案 |
| `obs_index` | INT | 可空 | 观测序号 |
| `metric_code` | TEXT | NOT NULL | 指标代码 |
| `value` | DOUBLE PRECISION | NOT NULL | 实测值 |
| `unit` | TEXT | 可空 | 单位 |
| `source` | TEXT | 可空 | 数据来源 |
| `measurement_quality` | TEXT | 可空 | 数据质量 |

| 约束/索引 | 定义 |
|---|---|
| 唯一约束 | `(plan_id, obs_index, metric_code)` |

---

#### `obs_timeseries` — 观测时序

每天的实测数据，如每日土壤水分、棚内温度、长势评分。与预测日指标对齐后可计算偏差。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `plan_id` | BIGINT | PK, FK → `plan.id`, ON DELETE CASCADE | 所属方案 |
| `day` | DATE | PK | 日期 |
| `metric_code` | TEXT | PK | 指标代码 |
| `value` | DOUBLE PRECISION | NOT NULL | 实测值 |
| `unit` | TEXT | 可空 | 单位 |
| `source` | TEXT | 可空 | 数据来源 |

| 约束/索引 | 定义 |
|---|---|
| 主键 | `(plan_id, day, metric_code)` |
| 索引 | `idx_obs_timeseries_metric(plan_id, metric_code)` |

---

## 4. 视图定义

### `v_plan_overview` — 方案概览

| 字段 | 来源 | 说明 |
|---|---|---|
| `plan_id` | `plan.id` | 方案 ID |
| `plan_code` | `plan.plan_code` | 方案代码 |
| `plan_name` | `plan.plan_name` | 方案名称 |
| `plan_status` | `plan.plan_status` | 状态 |
| `site_name` | `site.site_name` | 地块名称 |
| `crop_name` | `crop.crop_name` | 作物 |
| `variety_name` | `crop_variety.variety_name` | 品种 |
| `crop_start_date` | `plan.crop_start_date` | 播种/定植日期 |
| `expected_harvest_date` | `plan.expected_harvest_date` | 预计采收日期 |
| `expected_yield` | `plan_result.expected_yield` | 预期产量 |
| `score` | `plan_result.score` | 综合评分 |
| `risk_level` | `plan_result.risk_level` | 风险等级 |
| `reason_summary` | `plan_result.reason_summary` | 推荐理由 |

### `v_plan_tasks` — 任务时间线

| 字段 | 来源 | 说明 |
|---|---|---|
| `plan_id` | `plan.id` | 方案 ID |
| `plan_name` | `plan.plan_name` | 方案名称 |
| `task_date` | `plan_task.task_date` | 任务日期 |
| `task_type` | `plan_task.task_type` | 任务类型 |
| `task_title` | `plan_task.task_title` | 任务标题 |
| `trigger_type` | `plan_task.trigger_type` | 触发方式 |
| `status` | `plan_task.status` | 状态 |

### `v_prediction_daily` — 预测日指标

| 字段 | 来源 | 说明 |
|---|---|---|
| `run_id` | `prediction_run.id` | 运行 ID |
| `plan_id` | `prediction_run.plan_id` | 方案 ID |
| `run_code` | `prediction_run.run_code` | 运行代码 |
| `run_status` | `prediction_run.run_status` | 状态 |
| `day` | `prediction_daily.day` | 日期 |
| `metric_code` | `prediction_daily.metric_code` | 指标代码 |
| `value` | `prediction_daily.value` | 数值 |

### `v_obs_vs_plan` — 实测 vs 预测

| 字段 | 来源 | 说明 |
|---|---|---|
| `run_id` | `prediction_run.id` | 运行 ID |
| `plan_id` | `prediction_run.plan_id` | 方案 ID |
| `day` | `obs_timeseries.day` | 日期 |
| `metric_code` | `obs_timeseries.metric_code` | 指标代码 |
| `observed_value` | `obs_timeseries.value` | 实测值 |
| `predicted_value` | `prediction_daily.value` | 预测值 |
| `residual` | `predicted_value - observed_value` | 偏差 |

---

## 5. 方案生成流程

### 5.1 用户提交需求

用户直接创建 `plan`（草稿状态），填写地块、作物、品种、期望日期和目标。

### 5.2 系统读取输入数据

1. 读取 `site` + `soil_profile` + `site_condition` 确定地块环境
2. 读取 `weather_record` 获取气象数据
3. 读取 `crop` + `crop_variety` + `crop_param_set` + `crop_param_value` 获取品种参数
4. 读取 `algorithm` + `parameter_dict` + `metric_dict` 确定算法和指标

### 5.3 算法生成

1. 创建 `prediction_run`，调用算法执行
2. 日预测值写入 `prediction_daily`
3. 根据预测结果生成 `plan_task`（农事任务）和 `plan_trigger`（触发规则）
4. 汇总结果写入 `plan_result`

### 5.4 用户执行

1. 用户按 `plan_task` 的任务日程操作
2. 实际操作记录写入 `plan_operation`
3. 实测数据写入 `obs_summary` 或 `obs_timeseries`

### 5.5 复盘

1. 通过 `v_obs_vs_plan` 对比预测与实测偏差
2. 复盘结果用于优化下一轮参数和方案

---

## 6. 实施优先级

### P0：跑通单方案完整流程

实现：`algorithm`、`parameter_dict`、`metric_dict`、`crop`、`crop_variety`、`crop_param_set`、`crop_param_value`、`soil_profile`、`soil_profile_layer`、`site`、`site_condition`、`weather_source`、`weather_record`、`plan`、`plan_task`、`plan_result`。

**验收**：用户录入地块和品种后，能生成包含种植日历、农事任务和预期结果的完整方案。

### P1：条件触发 + 多方案对比 + 预测详情

增加：`plan_trigger`、`prediction_run`、`prediction_daily`、`obs_summary`、`obs_timeseries`。

**验收**：支持条件触发任务、多方案评分对比、预测日指标查看。

### P2：土壤模板 + 响应曲线 + 执行复盘

增加：`soil_type`、`response_curve`、`response_curve_point`、`plan_operation`。

**验收**：支持按土壤类型模板快速录入，响应曲线参数，执行偏差复盘分析。

---

## 7. ER 关系图

```text
crop ──1:N── crop_variety ──1:N── crop_param_set ──1:N── crop_param_value
                                         │                        │
                                    FK→algorithm            FK→response_curve
                                                                   │
                                                            response_curve_point

site ──1:N── site_condition ──FK── soil_profile ──1:N── soil_profile_layer
 │                                                           │
 └──1:N── weather_record ←── weather_source              soil_type

plan ──1:1── plan_result
  │
  ├──1:N── plan_task
  │
  ├──1:N── plan_trigger
  │
  ├──1:N── prediction_run ──1:N── prediction_daily
  │
  ├──1:N── plan_operation
  │
  ├──1:N── obs_summary
  │
  └──1:N── obs_timeseries
```
