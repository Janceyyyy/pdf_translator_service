# PDF Translator Service

这是一个简化版的PDF翻译服务，专为Render部署设计，可以与secondlanguage Chrome扩展配合使用。

## 功能

- PDF文件翻译
- 支持多种语言之间的翻译
- 多种PDF渲染模式：仅翻译、并排显示、交错显示
- RESTful API接口

## 部署到Render

### 使用Docker部署（推荐）

1. 在Render.com上注册账号
2. 创建一个新的**Web Service**
3. 连接到包含此代码的GitHub仓库
4. 选择**Docker**作为环境
5. 设置必要的环境变量（如需）
6. 点击**Create Web Service**

### 使用Python部署

1. 在Render.com上注册账号
2. 创建一个新的**Web Service**
3. 连接到包含此代码的GitHub仓库
4. 环境选择**Python**
5. 构建命令设置为: `pip install -r requirements.txt`
6. 启动命令设置为: `python server.py`
7. 点击**Create Web Service**

## API使用

### 获取支持的语言

```
GET /languages
```

返回支持的语言列表。

### 翻译PDF文件

```
POST /translate_pdf/
```

参数:
- `input_pdf`: PDF文件（可选，文件上传）
- `input_pdf_path`: PDF文件路径（可选，如果已在服务器上）
- `from_lang`: 源语言
- `to_lang`: 目标语言
- `translate_all`: 是否翻译所有页面
- `p_from`: 起始页码
- `p_to`: 结束页码
- `render_mode`: 渲染模式 (TRANSLATION_ONLY/SIDE_BY_SIDE/INTERLEAVE)
- `output_file_path`: 输出文件路径（可选）

返回翻译后的PDF文件。

### 示例: 使用CURL请求翻译

```bash
curl -X POST "https://your-render-service.onrender.com/translate_pdf/" \
  -F "input_pdf=@/path/to/your/file.pdf" \
  -F "from_lang=English" \
  -F "to_lang=Chinese" \
  -F "translate_all=true" \
  -F "p_from=0" \
  -F "p_to=0" \
  -F "render_mode=INTERLEAVE" \
  -o translated.pdf
```

## 与Chrome扩展配合使用

1. 在Chrome扩展的manifest.json中添加Render服务域名到`permissions`和`host_permissions`
2. 在扩展的background.js或其他相关文件中设置API端点为Render服务URL
3. 使用fetch或XMLHttpRequest向Render服务发送翻译请求

### 示例代码:

```javascript
// 在Chrome扩展中调用PDF翻译服务
async function translatePDF(pdfData, fromLang, toLang) {
  const formData = new FormData();
  formData.append('input_pdf', new Blob([pdfData], {type: 'application/pdf'}), 'document.pdf');
  formData.append('from_lang', fromLang);
  formData.append('to_lang', toLang);
  formData.append('translate_all', 'true');
  formData.append('p_from', '0');
  formData.append('p_to', '0');
  formData.append('render_mode', 'INTERLEAVE');

  const response = await fetch('https://your-render-service.onrender.com/translate_pdf/', {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    throw new Error('翻译失败');
  }

  return await response.blob();
}
```

## 本地开发

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 运行服务:
```bash
python server.py
```

服务将在本地的8765端口运行。

## 依赖项

详见requirements.txt文件。主要依赖包括:
- FastAPI
- uvicorn
- PyPDF2
- pdf2image
- reportlab
- googletrans==4.0.0-rc1 