class MarkdownEditor {
    constructor() {
        this.editor = document.getElementById('editor');
        this.preview = document.getElementById('preview');
        this.wordCount = document.querySelector('.word-count');
        this.fileInput = document.getElementById('fileInput');
        this.fileName = document.getElementById('fileName');
        this.toc = document.getElementById('toc');
        this.currentFile = null;
        this.isElectron = window.require && typeof window.require === 'function';
        this.ipcRenderer = this.isElectron ? window.require('electron').ipcRenderer : null;
        this.editorPanel = document.getElementById('editorPanel');
        this.editorVisible = false;
        
        this.initEventListeners();
        this.hideEditor();
    }
    
    initEventListeners() {
        // 实时预览
        this.editor.addEventListener('input', () => {
            this.updatePreview();
            this.updateWordCount();
        });
        
        // 快捷键支持
        this.editor.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key.toLowerCase()) {
                    case 'b':
                        e.preventDefault();
                        this.insertText('**', '**');
                        break;
                    case 'i':
                        e.preventDefault();
                        this.insertText('*', '*');
                        break;
                    case 's':
                        e.preventDefault();
                        if (!e.shiftKey) {
                            this.saveFile();
                        }
                        break;
                    case 'o':
                        e.preventDefault();
                        this.openFile();
                        break;
                }
            }
        });
        
        // 工具栏按钮
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.handleToolAction(action);
            });
        });
        
        // 保存按钮
        document.getElementById('saveBtn').addEventListener('click', () => {
            this.saveFile();
        });
        
        // 打开按钮
        document.getElementById('openBtn').addEventListener('click', () => {
            this.openFile();
        });
        
        // 切换编辑区按钮
        document.getElementById('toggleEditorBtn').addEventListener('click', () => {
            this.toggleEditor();
        });
        
        // 文件选择（非Electron环境）
        this.fileInput.addEventListener('change', (e) => {
            this.loadFile(e.target.files[0]);
        });
        
        // Electron IPC监听
        if (this.ipcRenderer) {
            // 监听主进程发送的文件打开事件
            this.ipcRenderer.on('open-file', (event, filePath) => {
                this.loadFileFromPath(filePath);
            });
            
            // 监听文件打开结果
            this.ipcRenderer.on('file-opened', (event, data) => {
                this.editor.value = data.content;
                this.currentFile = data.filePath;
                this.updatePreview();
                this.updateWordCount();
                const fileName = data.filePath.split('/').pop();
                this.updateFileName(fileName);
                this.showToast(`已打开: ${fileName}`);
            });
            
            // 监听文件保存结果
            this.ipcRenderer.on('file-saved', (event, filePath) => {
                this.currentFile = filePath;
                const fileName = filePath.split('/').pop();
                this.updateFileName(fileName);
                this.showToast(`已保存: ${fileName}`);
            });
        }
    }
    
    updatePreview() {
        const markdown = this.editor.value;
        const html = this.parseMarkdown(markdown);
        this.preview.innerHTML = html;
        this.attachHeadingClickHandlers();
        this.generateTableOfContents();
    }
    
    updateWordCount() {
        const text = this.editor.value;
        const count = text.length;
        this.wordCount.textContent = `${count} 字`;
    }
    
    parseMarkdown(text) {
        let html = text;
        
        // 转义HTML
        html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        
        // 标题（添加id用于跳转）
        html = html.replace(/^### (.*$)/gim, (match, text) => `<h3 id="${this.generateHeadingId(text)}">${text}</h3>`);
        html = html.replace(/^## (.*$)/gim, (match, text) => `<h2 id="${this.generateHeadingId(text)}">${text}</h2>`);
        html = html.replace(/^# (.*$)/gim, (match, text) => `<h1 id="${this.generateHeadingId(text)}">${text}</h1>`);
        
        // 粗体和斜体
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // 删除线
        html = html.replace(/~~(.*?)~~/g, '<del>$1</del>');
        
        // 行内代码
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 代码块
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // 引用
        html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');
        
        // 列表
        html = html.replace(/^(\s*)- (.*$)/gim, '$1<ul><li>$2</li></ul>');
        html = html.replace(/^(\s*)\d+\. (.*$)/gim, '$1<ol><li>$2</li></ol>');
        
        // 处理连续列表项
        html = html.replace(/<\/li><\/(ul|ol)>\s*<\1><li>/g, '</li><li>');
        
        // 链接
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        
        // 图片
        html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">');
        
        // 分割线
        html = html.replace(/^---$/gim, '<hr>');
        
        // 表格
        html = html.replace(/^(\|.*\|)$\n^(\|[-:| ]+\|)$\n((?:\|.*\|\n?)+)/gm, (match, header, separator, body) => {
            const headerCells = header.split('|').filter(cell => cell.trim());
            const bodyRows = body.trim().split('\n');
            let table = '<table><thead><tr>';
            headerCells.forEach(cell => {
                table += `<th>${cell.trim()}</th>`;
            });
            table += '</tr></thead><tbody>';
            bodyRows.forEach(row => {
                const cells = row.split('|').filter(cell => cell.trim());
                table += '<tr>';
                cells.forEach(cell => {
                    table += `<td>${cell.trim()}</td>`;
                });
                table += '</tr>';
            });
            table += '</tbody></table>';
            return table;
        });
        
        // 段落
        html = html.replace(/^(?!<[a-z])((?!<\/)[^\n])*$/gim, (match) => {
            if (!match.trim() || match.startsWith('<')) return match;
            return `<p>${match}</p>`;
        });
        
        // 换行
        html = html.replace(/\n/g, '<br>');
        
        // 清理多余的标签
        html = html.replace(/<p><\/p>/g, '');
        
        return html;
    }
    
    insertText(before, after = '') {
        const textarea = this.editor;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.substring(start, end);
        
        const newText = textarea.value.substring(0, start) + 
                        before + selectedText + after + 
                        textarea.value.substring(end);
        
        textarea.value = newText;
        
        // 设置光标位置
        if (selectedText) {
            textarea.setSelectionRange(start + before.length, end + before.length);
        } else {
            textarea.setSelectionRange(start + before.length, start + before.length);
        }
        
        textarea.focus();
        this.updatePreview();
        this.updateWordCount();
    }
    
    handleToolAction(action) {
        switch(action) {
            case 'bold':
                this.insertText('**', '**');
                break;
            case 'italic':
                this.insertText('*', '*');
                break;
            case 'heading1':
                this.insertText('# ', '');
                break;
            case 'heading2':
                this.insertText('## ', '');
                break;
            case 'list':
                this.insertText('- ', '');
                break;
            case 'code':
                this.insertText('`', '`');
                break;
            case 'link':
                this.insertText('[', '](url)');
                break;
            case 'image':
                this.insertText('![', '](image-url)');
                break;
        }
    }
    
    saveFile() {
        const content = this.editor.value;
        
        if (this.isElectron && this.ipcRenderer) {
            // Electron环境：使用IPC通信
            this.ipcRenderer.send('save-file-dialog', content);
        } else {
            // 浏览器环境：使用Blob下载
            const blob = new Blob([content], { type: 'text/markdown' });
            
            if (this.currentFile) {
                const filename = this.currentFile.name || 'document.md';
                this.downloadFile(blob, filename);
            } else {
                const filename = prompt('输入文件名:', 'document.md');
                if (filename) {
                    const name = filename.endsWith('.md') ? filename : filename + '.md';
                    this.downloadFile(blob, name);
                }
            }
        }
    }
    
    downloadFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.showToast('文件已下载');
    }
    
    openFile() {
        if (this.isElectron && this.ipcRenderer) {
            // Electron环境：使用IPC通信
            this.ipcRenderer.send('open-file-dialog');
        } else {
            // 浏览器环境：使用input file
            this.fileInput.click();
        }
    }
    
    loadFile(file) {
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            this.editor.value = e.target.result;
            this.currentFile = file;
            this.updatePreview();
            this.updateWordCount();
            this.updateFileName(file.name);
            this.showToast(`已打开: ${file.name}`);
        };
        reader.readAsText(file);
    }
    
    loadFileFromPath(filePath) {
        if (this.isElectron) {
            const fs = window.require('fs');
            const content = fs.readFileSync(filePath, 'utf-8');
            this.editor.value = content;
            this.currentFile = filePath;
            this.updatePreview();
            this.updateWordCount();
            const fileName = filePath.split('\\').pop();
            this.updateFileName(fileName);
            this.showToast(`已打开: ${fileName}`);
        }
    }
    
    showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            background-color: #2d3748;
            color: white;
            border-radius: 8px;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.3s ease;
            z-index: 1000;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '1';
        }, 10);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 2000);
    }
    
    toggleEditor() {
        this.editorVisible = !this.editorVisible;
        
        if (this.editorVisible) {
            this.showEditor();
        } else {
            this.hideEditor();
        }
        
        this.showToast(this.editorVisible ? '已显示编辑区' : '已隐藏编辑区');
    }
    
    showEditor() {
        this.editorPanel.style.display = 'flex';
    }
    
    hideEditor() {
        this.editorPanel.style.display = 'none';
    }
    
    generateHeadingId(text) {
        return 'heading-' + text.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-').replace(/^-|-$/g, '');
    }
    
    attachHeadingClickHandlers() {
        const headings = this.preview.querySelectorAll('h1, h2, h3');
        headings.forEach((heading) => {
            heading.style.cursor = 'pointer';
            heading.addEventListener('click', (e) => {
                const headingId = e.target.id;
                if (headingId) {
                    // 点击预览区标题时不显示编辑区，只滚动预览区
                    this.scrollToHeading(headingId, false);
                }
            });
        });
    }
    
    updateFileName(name) {
        if (this.fileName) {
            this.fileName.textContent = name || '未命名.md';
        }
    }
    
    generateTableOfContents() {
        const markdown = this.editor.value;
        const lines = markdown.split('\n');
        const headings = [];
        
        lines.forEach((line) => {
            if (line.startsWith('# ')) {
                headings.push({ level: 1, text: line.substring(2).trim() });
            } else if (line.startsWith('## ')) {
                headings.push({ level: 2, text: line.substring(3).trim() });
            } else if (line.startsWith('### ')) {
                headings.push({ level: 3, text: line.substring(4).trim() });
            }
        });
        
        if (headings.length === 0) {
            this.toc.innerHTML = '<div class="toc-empty">暂无目录</div>';
            return;
        }
        
        let tocHtml = '<ul class="toc-list">';
        headings.forEach((heading) => {
            const id = this.generateHeadingId(heading.text);
            const indent = heading.level > 1 ? 'style="padding-left: ' + (heading.level - 1) * 16 + 'px"' : '';
            tocHtml += `<li ${indent}><a href="#" class="toc-link" data-heading="${id}">${heading.text}</a></li>`;
        });
        tocHtml += '</ul>';
        
        this.toc.innerHTML = tocHtml;
        
        // 添加目录点击事件
        this.toc.querySelectorAll('.toc-link').forEach((link) => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const headingId = e.target.dataset.heading;
                // 点击侧边栏目录时不显示编辑区，只在预览区滚动
                this.scrollToHeading(headingId, false);
            });
        });
    }
    
    scrollToHeading(headingId, showEditor = true) {
        // 如果需要显示编辑区
        if (showEditor && !this.editorVisible) {
            this.showEditor();
            this.editorVisible = true;
        }
        
        // 如果编辑区可见，跳转到编辑区对应的标题位置
        if (this.editorVisible) {
            const markdownText = this.editor.value;
            const lines = markdownText.split('\n');
            const targetId = headingId.replace('heading-', '');
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line.startsWith('#')) {
                    const text = line.replace(/^#+\s*/, '').trim();
                    const lineId = text.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-').replace(/^-|-$/g, '');
                    if (lineId === targetId) {
                        this.editor.focus();
                        const pos = lines.slice(0, i).reduce((acc, line) => acc + line.length + 1, 0);
                        this.editor.setSelectionRange(pos, pos);
                        this.editor.scrollTop = i * 24;
                        break;
                    }
                }
            }
        }
        
        // 始终滚动预览区到对应标题
        const headingElement = this.preview.querySelector(`#${headingId}`);
        if (headingElement) {
            headingElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

// 初始化编辑器
document.addEventListener('DOMContentLoaded', () => {
    new MarkdownEditor();
});