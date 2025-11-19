#!/usr/bin/env python3
"""
解析txt文件并恢复原始文件结构
文件格式: 文件路径 \n 行号→内容 \n -------------- \n 下一个文件...
"""

import re
from pathlib import Path


def parse_and_restore(txt_file_path: str):
    """解析txt文件并恢复所有文件到原始路径"""

    print(f"\n{'='*60}")
    print(f"处理文件: {txt_file_path}")
    print(f"{'='*60}\n")

    # 读取txt文件
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按分隔符分割
    file_blocks = content.split('--------------\n')

    files_created = 0
    files_skipped = 0

    for block in file_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')
        if len(lines) < 1:
            continue

        # 第一行是文件路径
        file_path = lines[0].strip()

        # 跳过空路径
        if not file_path:
            continue

        # 移除开头的 "./"
        if file_path.startswith('./'):
            file_path = file_path[2:]

        # 处理内容行,去掉行号前缀(格式: 数字→内容)
        content_lines = []
        for line in lines[1:]:
            # 使用正则表达式匹配行号前缀 "数字→"
            match = re.match(r'^\s*\d+→(.*)$', line)
            if match:
                content_lines.append(match.group(1))
            else:
                # 如果没有行号前缀,直接添加
                content_lines.append(line)

        # 合并内容
        file_content = '\n'.join(content_lines)

        # 创建完整路径
        full_path = Path('/Users/liujiaxiang/code') / file_path

        # 检查文件是否已存在
        if full_path.exists():
            print(f"⚠️  跳过已存在的文件: {file_path}")
            files_skipped += 1
            continue

        # 创建目录(如果不存在)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(file_content)

        print(f"✅ 创建: {file_path}")
        files_created += 1

    print(f"\n{'='*60}")
    print(f"完成! 创建了 {files_created} 个文件, 跳过了 {files_skipped} 个已存在的文件")
    print(f"{'='*60}\n")


def main():
    """主函数"""

    # 处理两个txt文件
    txt_files = [
        '/Users/liujiaxiang/code/all_frontend_files.txt',
        '/Users/liujiaxiang/code/all_python_files.txt'
    ]

    total_created = 0
    total_skipped = 0

    for txt_file in txt_files:
        if not Path(txt_file).exists():
            print(f"❌ 文件不存在: {txt_file}")
            continue

        parse_and_restore(txt_file)

    print(f"\n{'='*60}")
    print("所有文件处理完成!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
