# hb-table-design

伙伴云建表流程的第一步：将业务需求或现有 Excel / 截图，转化为可确认的表结构方案，供用户确认后交给 hb-table-build 建表。

不做字段搬运——分析字段含义与关联、识别背后的业务对象后重新设计。

## 输入

- 模糊的业务需求描述，如"做个工单管理"
- 线下表单、Excel、截图或其他系统的表单截图

## 输出

方案文档 `表结构设计.md`，自上而下：

- **系统说明**：面向搭建者的施工概览（覆盖哪几个模块、共几张表、关键设计取舍）
- **业务流程图**：L1 主干、按模块分组的 SVG，每个环节标注其对应的数据表
- **ER 图**：PlantUML 渲染为 PNG，品牌配色，与流程图 / HTML 视觉统一
- **表格清单**：表名 / 类型 / 用途
- **字段清单**：每张表的全部字段（类型 / 必填 / 唯一 / 备注）

完成后可选导出**单文件 HTML**（图片 base64 内嵌、无外部依赖，可直接发客户、阅读体验更好）。

## 设计依据

- `reference/表结构设计原则.md`：三层十条原则 + 质量门
- `reference/字段选型规则.md`：伙伴云字段类型体系 + 选型判断
- `reference/表分类与分组.md`：4 类表（主数据 / 业务表 / 基础数据 / 配置表）+ 分组规则

## 脚本

```bash
# ER 图：PlantUML → PNG（官方服务器渲染，无需 Java/Graphviz，联网即用）
python3 scripts/plantuml_render.py er.puml er.png

# 业务流程图：JSON → SVG（纯标准库，本地渲染无网络依赖）
python3 scripts/flow_render.py flow.json flow.svg

# 导出单文件 HTML（图片内嵌，可直接发客户）
python3 scripts/md_to_html.py 表结构设计.md
```

完整流程、ER 语法与输出格式见 [SKILL.md](SKILL.md)，版本变更见 `CHANGELOG/`。
