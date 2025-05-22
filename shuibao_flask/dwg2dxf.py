# parse_dxf_to_json.py

import ezdxf
import json
import os
import sys

def json_to_markdown(json_path, output_md_path):
    """将JSON文件转换为Markdown格式"""
    try:
        # 读取JSON文件
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建Markdown内容
        md_content = []
        
        # 添加文件信息
        md_content.append(f"# {data['file']} 解析结果\n")
        
        # 添加图层信息
        md_content.append("## 图层信息\n")
        for layer, types in data['layers'].items():
            md_content.append(f"### 图层: {layer}")
            md_content.append("包含的图元类型:")
            for type_name in set(types):
                md_content.append(f"- {type_name}")
            md_content.append("")
        
        # 添加图元详细信息
        md_content.append("## 图元详细信息\n")
        for entity in data['entities']:
            md_content.append(f"### 图元类型: {entity['type']}")
            md_content.append(f"图层: {entity['layer']}")
            
            if entity['type'] == 'LINE':
                md_content.append(f"起点: {entity['start']}")
                md_content.append(f"终点: {entity['end']}")
            elif entity['type'] == 'CIRCLE':
                md_content.append(f"圆心: {entity['center']}")
                md_content.append(f"半径: {entity['radius']}")
            elif entity['type'] == 'TEXT':
                md_content.append(f"文本内容: {entity['text']}")
                md_content.append(f"位置: {entity['position']}")
            elif entity['type'] == 'LWPOLYLINE':
                md_content.append("顶点坐标:")
                for point in entity['points']:
                    md_content.append(f"- {point}")
            
            md_content.append("")
        
        # 写入Markdown文件
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        
        print(f"[成功] 已将JSON转换为Markdown: {output_md_path}")
        return True
        
    except Exception as e:
        print(f"[错误] 转换JSON到Markdown失败: {e}")
        return False

def parse_dxf_to_json(dxf_path, output_json_path=None):
    if not os.path.exists(dxf_path):
        print(f"[错误] 文件未找到: {dxf_path}")
        return

    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"[错误] 解析 DXF 文件失败: {e}")
        return

    msp = doc.modelspace()

    parsed_data = {
        "file": os.path.basename(dxf_path),
        "layers": {},
        "entities": []
    }

    for entity in msp:
        try:
            entity_info = {
                "type": entity.dxftype(),
                "layer": entity.dxf.layer,
            }

            if entity.dxftype() == 'LINE':
                entity_info["start"] = list(entity.dxf.start)
                entity_info["end"] = list(entity.dxf.end)

            elif entity.dxftype() == 'CIRCLE':
                entity_info["center"] = list(entity.dxf.center)
                entity_info["radius"] = entity.dxf.radius

            elif entity.dxftype() == 'TEXT':
                entity_info["text"] = entity.dxf.text
                entity_info["position"] = list(entity.dxf.insert)

            elif entity.dxftype() == 'LWPOLYLINE':
                entity_info["points"] = [list(p) for p in entity.get_points()]

            parsed_data["entities"].append(entity_info)

            layer_name = entity_info["layer"]
            parsed_data["layers"].setdefault(layer_name, [])
            parsed_data["layers"][layer_name].append(entity_info["type"])

        except Exception as e:
            print(f"[警告] 解析图元失败: {e}")

    # 设置默认输出路径
    if not output_json_path:
        output_json_path = os.path.splitext(dxf_path)[0] + "_parsed.json"

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, indent=4, ensure_ascii=False)

    print(f"[成功] 已生成结构化数据文件: {output_json_path}")
    return output_json_path

if __name__ == "__main__":
    # 设置输入输出路径
    input_path = r"D:\水保项目\巴塘水保\水保需材料\水保需材料\一审后修改图\围墙、大门施工图0427\围墙、大门施工图\door_output\大门结构.dxf"
    json_path = r"D:\水保项目\巴塘水保\水保需材料\水保需材料\一审后修改图\围墙、大门施工图0427\围墙、大门施工图\door_output\大门结构.json"
    md_path = r"D:\水保项目\巴塘水保\水保需材料\水保需材料\一审后修改图\围墙、大门施工图0427\围墙、大门施工图\door_output\大门结构.md"
    
    try:
        # 首先解析DXF文件生成JSON
        json_path = parse_dxf_to_json(input_path, json_path)
        if json_path:
            # 然后将JSON转换为Markdown
            json_to_markdown(json_path, md_path)
            # 可以选择是否删除JSON文件
            # os.remove(json_path)
    except Exception as e:
        print(f"程序执行失败: {str(e)}")
