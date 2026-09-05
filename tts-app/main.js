const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { MsEdgeTTS } = require('msedge-tts');

let mainWindow;
let edgeTTS = null;
let customVoices = [];

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 750,
        minWidth: 800,
        minHeight: 600,
        title: 'Text to Speech',
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

async function initTTS() {
    if (!edgeTTS) {
        edgeTTS = new MsEdgeTTS();
    }
    return edgeTTS;
}

async function getAvailableVoices() {
    const tts = await initTTS();
    const voices = await tts.getVoices();
    
    const groupedVoices = {
        zh: voices.filter(v => v.Locale.startsWith('zh')),
        en: voices.filter(v => v.Locale.startsWith('en')),
        other: voices.filter(v => !v.Locale.startsWith('zh') && !v.Locale.startsWith('en'))
    };
    
    return {
        edgeVoices: groupedVoices,
        customVoices: customVoices
    };
}

async function generateSpeech(text, voiceName, rate = 1, pitch = 1) {
    const tts = await initTTS();
    
    const rateValue = `+${(rate - 1) * 100}%`;
    const pitchValue = `+${(pitch - 1) * 100}Hz`;
    
    const voices = await tts.getVoices();
    const voice = voices.find(v => v.ShortName === voiceName);
    if (!voice) {
        throw new Error('Voice not found');
    }
    
    await tts.setMetadata(
        voice.ShortName,
        voice.SuggestedCodec,
        {
            rate: rateValue,
            pitch: pitchValue,
            volume: '+0%'
        }
    );
    
    const { audioStream } = await tts.toStream(text);
    
    const chunks = [];
    return new Promise((resolve, reject) => {
        audioStream.on('data', (chunk) => {
            chunks.push(chunk);
        });
        audioStream.on('end', () => {
            resolve(Buffer.concat(chunks));
        });
        audioStream.on('error', (err) => {
            reject(err);
        });
    });
}

app.on('ready', createWindow);

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', function () {
    if (mainWindow === null) createWindow();
});

ipcMain.on('list-voices', async (event) => {
    try {
        const voices = await getAvailableVoices();
        event.reply('voices-loaded', voices);
    } catch (error) {
        event.reply('voices-loaded', { error: error.message });
    }
});

ipcMain.on('speak', async (event, { text, voiceName, rate, pitch }) => {
    try {
        const audioBuffer = await generateSpeech(text, voiceName, rate, pitch);
        event.reply('speech-generated', { audioBuffer: audioBuffer });
    } catch (error) {
        event.reply('speech-error', error.message);
    }
});

ipcMain.on('save-audio', async (event, { text, voiceName, rate, pitch }) => {
    try {
        const result = await dialog.showSaveDialog(mainWindow, {
            defaultPath: 'speech.mp3',
            filters: [
                { name: 'MP3 Files', extensions: ['mp3'] },
                { name: 'WAV Files', extensions: ['wav'] },
                { name: 'All Files', extensions: ['*'] }
            ]
        });

        if (result.canceled || !result.filePath) {
            event.reply('audio-saved', null);
            return;
        }

        const audioBuffer = await generateSpeech(text, voiceName, rate, pitch);
        fs.writeFileSync(result.filePath, audioBuffer);
        event.reply('audio-saved', result.filePath);
    } catch (error) {
        event.reply('audio-saved', null, error.message);
    }
});

ipcMain.on('add-custom-voice', async (event, voiceConfig) => {
    try {
        const existingVoice = customVoices.find(v => v.name === voiceConfig.name);
        if (existingVoice) {
            event.reply('custom-voice-added', { success: false, error: 'Voice name already exists' });
            return;
        }

        customVoices.push(voiceConfig);
        event.reply('custom-voice-added', { success: true, voice: voiceConfig });
    } catch (error) {
        event.reply('custom-voice-added', { success: false, error: error.message });
    }
});

ipcMain.on('remove-custom-voice', async (event, voiceName) => {
    try {
        customVoices = customVoices.filter(v => v.name !== voiceName);
        event.reply('custom-voice-removed', { success: true });
    } catch (error) {
        event.reply('custom-voice-removed', { success: false, error: error.message });
    }
});

ipcMain.on('open-text-file', async (event) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: [
            { name: 'Text Files', extensions: ['txt'] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });

    if (!result.canceled && result.filePaths.length > 0) {
        const filePath = result.filePaths[0];
        const content = fs.readFileSync(filePath, 'utf-8');
        event.reply('text-file-opened', { content, filePath });
    }
});