import sys
import os
import tempfile
import yaml
from pathlib import Path
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from PyPDF2 import PdfReader, PdfWriter
import time
import asyncio
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image
from loguru import logger
import io

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("pdf_translator.log", rotation="10 MB", level="INFO")

# 创建FastAPI实例
app = FastAPI(title="PDF Translator API", version="1.0")

# 添加CORS支持，允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载配置
def load_config():
    config_path = Path("config.yaml")
    if not config_path.exists():
        # 创建默认配置
        config = {
            "translator": {
                "type": "google",  # 默认使用Google翻译，因为不需要API密钥
                "api_key": "",
                "model": ""
            },
            "render": {
                "type": "reportlab",
                "font_name": "Arial",
                "render_mode": "INTERLEAVE"  # TRANSLATION_ONLY / SIDE_BY_SIDE / INTERLEAVE
            }
        }
        # 保存默认配置
        with open(config_path, "w") as f:
            yaml.dump(config, f)
    else:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    
    return config

# 加载配置
config = load_config()

# 简化的翻译类 - 使用Google翻译API
class SimpleTranslator:
    def __init__(self):
        try:
            from googletrans import Translator
            self.translator = Translator()
        except ImportError:
            logger.error("请安装googletrans库: pip install googletrans==4.0.0-rc1")
            self.translator = None
        
        self.languages = [
            "English", "Chinese", "Japanese", "Korean", "French", 
            "German", "Spanish", "Italian", "Russian", "Portuguese"
        ]
    
    def get_languages(self):
        return self.languages
    
    def translate_text(self, text, from_lang, to_lang):
        if not text.strip():
            return text
            
        if self.translator is None:
            return text
            
        # 语言代码转换
        lang_map = {
            "English": "en", "Chinese": "zh-cn", "Japanese": "ja",
            "Korean": "ko", "French": "fr", "German": "de",
            "Spanish": "es", "Italian": "it", "Russian": "ru",
            "Portuguese": "pt"
        }
        
        from_code = lang_map.get(from_lang, "auto")
        to_code = lang_map.get(to_lang, "en")
        
        try:
            result = self.translator.translate(text, src=from_code, dest=to_code)
            return result.text
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return text

# 简化的PDF渲染类
class SimplePdfRenderer:
    def __init__(self):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, Frame
        
        # 尝试注册一些通用字体
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
        except:
            logger.warning("无法加载Arial字体，使用内置字体代替")
    
    def render_translated_pdf(self, original_pdf_path, translated_texts, output_path, mode="INTERLEAVE"):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from PyPDF2 import PdfReader, PdfWriter
        from reportlab.platypus import Paragraph, Frame
        from reportlab.lib.styles import getSampleStyleSheet
        
        # 读取原始PDF
        original_pdf = PdfReader(original_pdf_path)
        output_pdf = PdfWriter()
        
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # 处理每一页
        for i, page_text in enumerate(translated_texts):
            if i >= len(original_pdf.pages):
                break
                
            # 获取原始页面
            original_page = original_pdf.pages[i]
            width, height = original_page.mediabox.width, original_page.mediabox.height
            
            # 创建一个新的PDF页面
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(width, height))
            
            # 根据模式渲染
            if mode == "TRANSLATION_ONLY":
                # 仅显示翻译
                frame = Frame(36, 36, width-72, height-72, id='normal')
                story = [Paragraph(page_text, normal_style)]
                frame.addFromList(story, c)
            elif mode == "SIDE_BY_SIDE":
                # 原文和翻译并排显示
                frame_width = (width-72) / 2
                
                # 左侧原文
                frame_original = Frame(36, 36, frame_width-18, height-72, id='original')
                story_original = [Paragraph("ORIGINAL TEXT PLACEHOLDER", normal_style)]
                frame_original.addFromList(story_original, c)
                
                # 右侧翻译
                frame_trans = Frame(36 + frame_width + 18, 36, frame_width-18, height-72, id='translation')
                story_trans = [Paragraph(page_text, normal_style)]
                frame_trans.addFromList(story_trans, c)
            else:  # INTERLEAVE
                # 交错显示原文和翻译
                frame = Frame(36, 36, width-72, height-72, id='interleave')
                story = [
                    Paragraph("ORIGINAL TEXT PLACEHOLDER", normal_style),
                    Paragraph(page_text, normal_style)
                ]
                frame.addFromList(story, c)
            
            c.save()
            
            # 获取PDF内容
            packet.seek(0)
            new_pdf = PdfReader(packet)
            new_page = new_pdf.pages[0]
            
            # 如果不是仅翻译模式，需要合并原始页面
            if mode != "TRANSLATION_ONLY":
                new_page.merge_page(original_page)
            
            # 添加到输出PDF
            output_pdf.add_page(new_page)
        
        # 保存最终PDF
        with open(output_path, "wb") as f:
            output_pdf.write(f)
        
        return output_path

# 初始化翻译器和渲染器
translator = SimpleTranslator()
renderer = SimplePdfRenderer()

# 存储临时目录
temp_dir = tempfile.TemporaryDirectory()
temp_dir_path = Path(temp_dir.name)
logger.info(f"使用临时目录: {temp_dir_path}")

# 创建下载和翻译目录
download_dir = Path("download")
download_dir.mkdir(exist_ok=True)
translate_dir = Path("translate")
translate_dir.mkdir(exist_ok=True)

# API路由
@app.get("/")
async def root():
    return {"message": "PDF翻译服务已启动", "version": "1.0"}

@app.get("/languages")
async def get_languages():
    return {"languages": translator.get_languages()}

@app.post("/translate_pdf/")
async def translate_pdf(
    input_pdf: UploadFile = File(None),
    input_pdf_path: str = Form(None),
    from_lang: str = Form(...),
    to_lang: str = Form(...),
    translate_all: bool = Form(...),
    p_from: int = Form(...),
    p_to: int = Form(...),
    render_mode: str = Form(...),
    output_file_path: str = Form(None),
    add_blank_page: bool = Form(False),
    background_tasks: BackgroundTasks = None,
):
    """API终点用于翻译PDF文件"""
    logger.info(
        f"收到翻译PDF请求:\nfrom_lang: {from_lang} to_lang: {to_lang}\n"
        f"translate_all: {translate_all} p_from: {p_from}, p_to: {p_to}\n"
        f"render_mode: {render_mode}\noutput_file_path: {output_file_path}\n"
        f"input_pdf_path: {input_pdf_path}\ninput_pdf: {input_pdf is None}"
    )

    try:
        # 处理输入
        if input_pdf:
            input_pdf_data = await input_pdf.read()
            temp_input_path = temp_dir_path / input_pdf.filename
            with open(temp_input_path, "wb") as f:
                f.write(input_pdf_data)
                
            if not output_file_path:
                output_file_path = temp_dir_path / input_pdf.filename.replace(".pdf", "_translated.pdf")
        elif input_pdf_path:
            temp_input_path = Path(input_pdf_path)
            if not output_file_path:
                output_file_path = str(Path(input_pdf_path).with_suffix("")) + "_translated.pdf"
        else:
            return JSONResponse(status_code=400, content={"error": "没有提供PDF文件"})
            
        output_file_path = Path(output_file_path)

        # 读取PDF
        try:
            pdf = PdfReader(str(temp_input_path))
            num_pages = len(pdf.pages)
            logger.info(f"PDF有{num_pages}页")
        except Exception as e:
            logger.error(f"无法读取PDF: {e}")
            return JSONResponse(status_code=400, content={"error": f"无法读取PDF: {e}"})

        # 确定要翻译的页面范围
        if translate_all:
            page_range = range(num_pages)
        else:
            if p_to <= 0:
                p_to = num_pages - 1
            page_range = range(max(0, p_from), min(num_pages, p_to + 1))

        # 提取文本
        texts = []
        for i in page_range:
            try:
                page = pdf.pages[i]
                text = page.extract_text()
                texts.append(text)
            except Exception as e:
                logger.error(f"无法提取第{i+1}页文本: {e}")
                texts.append(f"[无法提取文本: {e}]")

        # 翻译文本
        translated_texts = []
        for i, text in enumerate(texts):
            try:
                logger.info(f"翻译第{list(page_range)[i]+1}页")
                translated = translator.translate_text(text, from_lang, to_lang)
                translated_texts.append(translated)
            except Exception as e:
                logger.error(f"翻译第{list(page_range)[i]+1}页失败: {e}")
                translated_texts.append(f"[翻译失败: {e}]")

        # 渲染翻译后的PDF
        try:
            renderer.render_translated_pdf(
                str(temp_input_path), 
                translated_texts, 
                str(output_file_path), 
                mode=render_mode
            )
            logger.info(f"翻译后的PDF保存到: {output_file_path}")
        except Exception as e:
            logger.error(f"渲染PDF失败: {e}")
            return JSONResponse(status_code=500, content={"error": f"渲染PDF失败: {e}"})

        # 返回翻译后的PDF
        return FileResponse(
            str(output_file_path),
            media_type="application/pdf",
            filename=output_file_path.name
        )
    except Exception as e:
        logger.error(f"翻译过程出错: {e}")
        return JSONResponse(status_code=500, content={"error": f"翻译过程出错: {e}"})

# 添加健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 主函数
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False) 