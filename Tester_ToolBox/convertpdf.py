import markdown
import pdfkit
import os

def convert_md_to_pdf(md_file='readme.md', output_pdf='readme.pdf'):
    """
    将Markdown文件转换为PDF
    
    Args:
        md_file: Markdown文件路径
        output_pdf: 输出PDF文件路径
    """
    print(f"开始转换 {md_file} 为PDF...")
    
    try:
        # 检查源文件是否存在
        if not os.path.exists(md_file):
            print(f"错误: 找不到源文件 {md_file}")
            return False
            
        # 读取markdown内容
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # 转换markdown为HTML
        html_content = markdown.markdown(md_content)
        
        # 添加HTML样式
        styled_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: "Microsoft YaHei", "Arial", sans-serif;
                    font-size: 12pt;
                    line-height: 1.6;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    font-family: "Microsoft YaHei", "Arial", sans-serif;
                }}
                code {{
                    font-family: "Consolas", monospace;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # 配置PDF转换选项
        options = {
            'encoding': 'UTF-8',
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'enable-local-file-access': True,
            'minimum-font-size': 12
        }
        
        # 转换为PDF
        pdfkit.from_string(styled_html, output_pdf, options=options)
        print(f"PDF文件已成功创建: {output_pdf}")
        return True
        
    except Exception as e:
        print(f"转换过程中出现错误: {str(e)}")
        return False

if __name__ == "__main__":
    convert_md_to_pdf()