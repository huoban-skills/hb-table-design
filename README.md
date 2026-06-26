# hb-table-design

分析客户需求和线下表格，生成表格设计方案（表结构图、表格/字段清单），为搭建表格提供完整方案。

## 输入

- 模糊的业务需求描述，如"做个工单管理"
- 线下表单、Excel、截图或其他系统的表单截图

## 输出

- **表结构图**：PlantUML ER 图渲染为 PNG，直观展示表与表的关系
- **表格清单**：每张表的名称、类型、用途
- **字段清单**：每张表的全部字段，含类型、必填、唯一、备注

## 设计依据

- `reference/表结构设计原则.md`：三层十条原则 + 质量门
- `reference/字段选型规则.md`：伙伴云字段类型体系 + 选型判断
- `reference/表分类与分组.md`：4 类表（主数据 / 业务表 / 基础数据 / 配置表）+ 分组规则

## 渲染脚本

```bash
python3 scripts/plantuml_render.py input.puml output.png
```

通过 PlantUML 官方服务器渲染，无需本地安装 Java 或 Graphviz，联网即用。
