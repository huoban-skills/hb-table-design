# hb-er-draw

伙伴云建表流程第一步：将业务需求转化为表结构方案，输出 ER 图（PNG）和字段清单，供用户确认后交给 hb-table-build 执行。

## 功能

- 从模糊需求或现有表单反推表结构（三层十条设计原则）
- 按伙伴云字段类型体系做字段选型
- 渲染 ER 图 PNG（通过 PlantUML 官方服务器，无需本地 Java）
- 输出字段清单 Markdown 文档

## 触发场景

用户说"画 ER 图"、"设计表结构"、"出方案"、"数据库设计"、"表关系图"，或建表需求不明确时触发。

## 文件结构

```
SKILL.md                    # Skill 主文件
reference/
  表结构设计原则.md          # 三层十条 + 质量门
  字段选型规则.md            # 伙伴云字段类型 + 选型判断
  表分类与分组.md            # 4 类表 + 分组规则
scripts/
  plantuml_render.py        # PlantUML → PNG/SVG 渲染脚本
```

## 渲染脚本

```bash
python3 scripts/plantuml_render.py input.puml output.png
```

无需安装 Java 或 Graphviz，联网即用。
