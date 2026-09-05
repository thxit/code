const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow;
let filePath = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        title: 'Markdown Editor',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true
        },
        icon: path.join(__dirname, 'icon.ico')
    });

    mainWindow.loadFile('index.html');

    mainWindow.on('closed', function () {
        mainWindow = null;
    });
}

app.on('ready', createWindow);

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', function () {
    if (mainWindow === null) createWindow();
});

// 处理文件拖拽打开
app.on('open-file', (event, path) => {
    event.preventDefault();
    filePath = path;
    if (mainWindow) {
        mainWindow.webContents.send('open-file', path);
    }
});

// 监听渲染进程请求打开文件
ipcMain.on('open-file-dialog', async (event) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: [
            { name: 'Markdown Files', extensions: ['md'] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });

    if (!result.canceled && result.filePaths.length > 0) {
        filePath = result.filePaths[0];
        const content = fs.readFileSync(filePath, 'utf-8');
        event.reply('file-opened', { content, filePath });
    }
});

// 监听渲染进程请求打开文件夹
ipcMain.on('open-folder-dialog', async (event) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });

    if (!result.canceled && result.filePaths.length > 0) {
        const folderPath = result.filePaths[0];
        try {
            const files = fs.readdirSync(folderPath)
                .filter(f => f.endsWith('.md'))
                .map(f => ({
                    name: f,
                    path: path.join(folderPath, f)
                }));
            event.reply('folder-opened', { folderPath, files });
        } catch (err) {
            event.reply('folder-opened', { folderPath, files: [], error: err.message });
        }
    }
});

// 监听渲染进程请求读取指定文件
ipcMain.on('read-file', (event, filePath) => {
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        event.reply('file-read', { content, filePath });
    } catch (err) {
        event.reply('file-read', { content: '', filePath, error: err.message });
    }
});

// 监听渲染进程请求保存文件
ipcMain.on('save-file-dialog', async (event, content) => {
    let targetPath = filePath;
    
    if (!targetPath) {
        const result = await dialog.showSaveDialog(mainWindow, {
            defaultPath: 'document.md',
            filters: [
                { name: 'Markdown Files', extensions: ['md'] },
                { name: 'All Files', extensions: ['*'] }
            ]
        });

        if (result.canceled) return;
        targetPath = result.filePath;
    }

    fs.writeFileSync(targetPath, content, 'utf-8');
    filePath = targetPath;
    event.reply('file-saved', targetPath);
});

// 检查是否有通过命令行传入的文件
if (process.argv.length > 1) {
    const argPath = process.argv[1];
    if (fs.existsSync(argPath) && fs.statSync(argPath).isFile()) {
        filePath = argPath;
    }
}

// 在窗口加载完成后发送初始文件路径
app.on('ready', () => {
    if (filePath) {
        mainWindow.webContents.on('did-finish-load', () => {
            mainWindow.webContents.send('open-file', filePath);
        });
    }
});