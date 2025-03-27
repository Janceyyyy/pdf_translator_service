/**
 * 示例代码: 从Chrome扩展调用PDF翻译服务
 * 这个文件演示了如何在secondlanguage扩展中集成PDF翻译功能
 */

// PDF翻译服务的URL
const PDF_TRANSLATOR_SERVICE_URL = "https://your-pdf-translator-service.onrender.com";

/**
 * 获取支持的语言列表
 * @returns {Promise<Array<string>>} 语言列表
 */
async function getSupportedLanguages() {
  try {
    const response = await fetch(`${PDF_TRANSLATOR_SERVICE_URL}/languages`);
    if (!response.ok) {
      throw new Error(`获取语言列表失败: ${response.status}`);
    }
    const data = await response.json();
    return data.languages;
  } catch (error) {
    console.error('获取语言列表出错:', error);
    throw error;
  }
}

/**
 * 翻译PDF文件
 * @param {ArrayBuffer} pdfData PDF文件数据
 * @param {string} fromLang 源语言
 * @param {string} toLang 目标语言
 * @param {Object} options 其他选项
 * @returns {Promise<Blob>} 翻译后的PDF文件
 */
async function translatePDF(pdfData, fromLang, toLang, options = {}) {
  const {
    translateAll = true,
    pageFrom = 0,
    pageTo = 0,
    renderMode = "INTERLEAVE"
  } = options;

  try {
    // 创建FormData对象
    const formData = new FormData();
    formData.append('input_pdf', new Blob([pdfData], {type: 'application/pdf'}), 'document.pdf');
    formData.append('from_lang', fromLang);
    formData.append('to_lang', toLang);
    formData.append('translate_all', translateAll);
    formData.append('p_from', pageFrom);
    formData.append('p_to', pageTo);
    formData.append('render_mode', renderMode);

    // 发送请求
    const response = await fetch(`${PDF_TRANSLATOR_SERVICE_URL}/translate_pdf/`, {
      method: 'POST',
      body: formData
    });

    // 检查响应状态
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`翻译PDF失败: ${response.status} ${errorText}`);
    }

    // 返回翻译后的PDF blob
    return await response.blob();
  } catch (error) {
    console.error('翻译PDF出错:', error);
    throw error;
  }
}

/**
 * 将翻译后的PDF显示在新标签页
 * @param {Blob} pdfBlob 翻译后的PDF Blob
 */
function displayTranslatedPDF(pdfBlob) {
  // 创建URL
  const pdfUrl = URL.createObjectURL(pdfBlob);
  
  // 在新标签页中打开
  chrome.tabs.create({ url: pdfUrl });
}

/**
 * 处理本地PDF文件
 * @param {File} file 本地PDF文件
 * @param {string} fromLang 源语言
 * @param {string} toLang 目标语言
 */
async function handleLocalPDFFile(file, fromLang, toLang) {
  try {
    // 显示加载状态
    setLoading(true);
    
    // 读取文件内容
    const fileData = await file.arrayBuffer();
    
    // 翻译PDF
    const translatedPdf = await translatePDF(fileData, fromLang, toLang);
    
    // 显示翻译后的PDF
    displayTranslatedPDF(translatedPdf);
  } catch (error) {
    console.error('处理PDF文件失败:', error);
    showError('处理PDF文件失败: ' + error.message);
  } finally {
    // 隐藏加载状态
    setLoading(false);
  }
}

/**
 * 从远程URL下载PDF
 * @param {string} url PDF的URL
 * @returns {Promise<ArrayBuffer>} PDF数据
 */
async function downloadPDF(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`下载PDF失败: ${response.status}`);
  }
  return await response.arrayBuffer();
}

/**
 * 处理远程PDF URL
 * @param {string} url PDF的URL
 * @param {string} fromLang 源语言
 * @param {string} toLang 目标语言
 */
async function handleRemotePDFUrl(url, fromLang, toLang) {
  try {
    // 显示加载状态
    setLoading(true);
    
    // 下载PDF
    const pdfData = await downloadPDF(url);
    
    // 翻译PDF
    const translatedPdf = await translatePDF(pdfData, fromLang, toLang);
    
    // 显示翻译后的PDF
    displayTranslatedPDF(translatedPdf);
  } catch (error) {
    console.error('处理远程PDF失败:', error);
    showError('处理远程PDF失败: ' + error.message);
  } finally {
    // 隐藏加载状态
    setLoading(false);
  }
}

/**
 * 集成到secondlanguage扩展的PDF翻译功能
 * 这个函数应该在popup.js或相关文件中调用
 */
function initPDFTranslator() {
  // 获取支持的语言列表并填充下拉菜单
  getSupportedLanguages().then(languages => {
    const fromLangSelect = document.getElementById('fromLangSelect');
    const toLangSelect = document.getElementById('toLangSelect');
    
    if (fromLangSelect && toLangSelect) {
      // 清空现有选项
      fromLangSelect.innerHTML = '';
      toLangSelect.innerHTML = '';
      
      // 添加语言选项
      languages.forEach(lang => {
        fromLangSelect.appendChild(new Option(lang, lang));
        toLangSelect.appendChild(new Option(lang, lang));
      });
      
      // 默认选项
      fromLangSelect.value = 'English';
      toLangSelect.value = 'Chinese';
    }
  }).catch(error => {
    console.error('初始化语言选择器失败:', error);
  });
  
  // 设置文件选择器监听
  const fileInput = document.getElementById('pdfFileInput');
  if (fileInput) {
    fileInput.addEventListener('change', (event) => {
      const file = event.target.files[0];
      if (file && file.type === 'application/pdf') {
        const fromLang = document.getElementById('fromLangSelect').value;
        const toLang = document.getElementById('toLangSelect').value;
        handleLocalPDFFile(file, fromLang, toLang);
      }
    });
  }
  
  // 设置URL输入监听
  const urlForm = document.getElementById('pdfUrlForm');
  if (urlForm) {
    urlForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const urlInput = document.getElementById('pdfUrlInput');
      if (urlInput && urlInput.value) {
        const fromLang = document.getElementById('fromLangSelect').value;
        const toLang = document.getElementById('toLangSelect').value;
        handleRemotePDFUrl(urlInput.value, fromLang, toLang);
      }
    });
  }
}

// 辅助函数
function setLoading(isLoading) {
  const loadingIndicator = document.getElementById('loadingIndicator');
  if (loadingIndicator) {
    loadingIndicator.style.display = isLoading ? 'block' : 'none';
  }
}

function showError(message) {
  const errorDisplay = document.getElementById('errorDisplay');
  if (errorDisplay) {
    errorDisplay.textContent = message;
    errorDisplay.style.display = 'block';
    setTimeout(() => {
      errorDisplay.style.display = 'none';
    }, 5000);
  }
}

// 导出函数，以便在扩展的其他地方使用
window.pdfTranslator = {
  getSupportedLanguages,
  translatePDF,
  displayTranslatedPDF,
  handleLocalPDFFile,
  handleRemotePDFUrl,
  initPDFTranslator
}; 