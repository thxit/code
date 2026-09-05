const { ipcRenderer } = require('electron');

const textInput = document.getElementById('text-input');
const voiceSelect = document.getElementById('voice-select');
const rateSlider = document.getElementById('rate-slider');
const pitchSlider = document.getElementById('pitch-slider');
const volumeSlider = document.getElementById('volume-slider');
const rateValue = document.getElementById('rate-value');
const pitchValue = document.getElementById('pitch-value');
const volumeValue = document.getElementById('volume-value');
const playBtn = document.getElementById('play-btn');
const pauseBtn = document.getElementById('pause-btn');
const stopBtn = document.getElementById('stop-btn');
const saveAudioBtn = document.getElementById('save-audio-btn');
const openFileBtn = document.getElementById('open-file-btn');
const manageVoicesBtn = document.getElementById('manage-voices-btn');
const statusText = document.getElementById('status-text');

const voiceModal = document.getElementById('voice-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const customVoiceName = document.getElementById('custom-voice-name');
const customVoiceShortname = document.getElementById('custom-voice-shortname');
const customVoiceLang = document.getElementById('custom-voice-lang');
const addVoiceBtn = document.getElementById('add-voice-btn');
const customVoicesList = document.getElementById('custom-voices-list');
const edgeVoicesList = document.getElementById('edge-voices-list');

let audio = null;
let edgeVoices = [];
let customVoices = [];
let isPlaying = false;

function updateStatus(message) {
    statusText.textContent = message;
}

function updateButtonStates(playing) {
    isPlaying = playing;
    playBtn.disabled = playing;
    pauseBtn.disabled = !playing;
    stopBtn.disabled = !playing;
}

function loadVoicesIntoSelect(voicesData) {
    voiceSelect.innerHTML = '';
    
    if (voicesData.error) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '加载失败';
        voiceSelect.appendChild(option);
        updateStatus('语音加载失败');
        return;
    }

    edgeVoices = voicesData.edgeVoices;
    customVoices = voicesData.customVoices || [];

    const zhVoices = edgeVoices.zh || [];
    const enVoices = edgeVoices.en || [];
    const otherVoices = edgeVoices.other || [];

    if (customVoices.length > 0) {
        const customGroup = document.createElement('optgroup');
        customGroup.label = '自定义音源';
        customVoices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.shortName;
            option.textContent = `⭐ ${voice.name} (${voice.lang})`;
            customGroup.appendChild(option);
        });
        voiceSelect.appendChild(customGroup);
    }

    if (zhVoices.length > 0) {
        const zhGroup = document.createElement('optgroup');
        zhGroup.label = '中文语音';
        zhVoices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.ShortName;
            option.textContent = `${voice.Name} (${voice.Language})`;
            zhGroup.appendChild(option);
        });
        voiceSelect.appendChild(zhGroup);
    }

    if (enVoices.length > 0) {
        const enGroup = document.createElement('optgroup');
        enGroup.label = '英文语音';
        enVoices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.ShortName;
            option.textContent = `${voice.Name} (${voice.Language})`;
            enGroup.appendChild(option);
        });
        voiceSelect.appendChild(enGroup);
    }

    if (otherVoices.length > 0) {
        const otherGroup = document.createElement('optgroup');
        otherGroup.label = '其他语音';
        otherVoices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.ShortName;
            option.textContent = `${voice.Name} (${voice.Language})`;
            otherGroup.appendChild(option);
        });
        voiceSelect.appendChild(otherGroup);
    }

    const defaultVoice = zhVoices.find(v => v.Language === 'zh-CN') || zhVoices[0] || enVoices[0] || otherVoices[0];
    if (defaultVoice) {
        voiceSelect.value = defaultVoice.ShortName;
    }

    updateStatus('语音加载完成');
}

function renderEdgeVoicesList() {
    edgeVoicesList.innerHTML = '';
    
    const voiceGroups = [
        { label: '中文语音', voices: edgeVoices.zh || [] },
        { label: '英文语音', voices: edgeVoices.en || [] },
        { label: '其他语音', voices: edgeVoices.other || [] }
    ];

    voiceGroups.forEach(group => {
        if (group.voices.length === 0) return;
        
        const groupDiv = document.createElement('div');
        groupDiv.className = 'voice-group';
        groupDiv.innerHTML = `<h4>${group.label}</h4>`;
        
        const list = document.createElement('ul');
        group.voices.forEach(voice => {
            const li = document.createElement('li');
            li.className = 'voice-item';
            li.innerHTML = `
                <span class="voice-name">${voice.Name}</span>
                <span class="voice-shortname">${voice.ShortName}</span>
                <span class="voice-lang">${voice.Language}</span>
                <span class="voice-gender">${voice.Gender || ''}</span>
            `;
            list.appendChild(li);
        });
        
        groupDiv.appendChild(list);
        edgeVoicesList.appendChild(groupDiv);
    });

    if (edgeVoicesList.children.length === 0) {
        edgeVoicesList.innerHTML = '<p class="empty-message">暂无可用音源</p>';
    }
}

function renderCustomVoicesList() {
    customVoicesList.innerHTML = '';
    
    if (customVoices.length === 0) {
        customVoicesList.innerHTML = '<p class="empty-message">暂无自定义音源</p>';
        return;
    }

    const list = document.createElement('ul');
    customVoices.forEach(voice => {
        const li = document.createElement('li');
        li.className = 'voice-item custom';
        li.innerHTML = `
            <span class="voice-name">⭐ ${voice.name}</span>
            <span class="voice-shortname">${voice.shortName}</span>
            <span class="voice-lang">${voice.lang}</span>
            <button class="remove-voice-btn" data-name="${voice.name}">删除</button>
        `;
        list.appendChild(li);
    });
    
    customVoicesList.appendChild(list);

    document.querySelectorAll('.remove-voice-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const voiceName = e.target.dataset.name;
            ipcRenderer.send('remove-custom-voice', voiceName);
        });
    });
}

async function speak() {
    const text = textInput.value.trim();
    if (!text) {
        updateStatus('请输入文本');
        return;
    }

    const voiceName = voiceSelect.value;
    if (!voiceName) {
        updateStatus('请选择语音');
        return;
    }

    updateStatus('正在生成语音...');
    updateButtonStates(true);

    ipcRenderer.send('speak', {
        text: text,
        voiceName: voiceName,
        rate: parseFloat(rateSlider.value),
        pitch: parseFloat(pitchSlider.value)
    });
}

function playAudio(audioBuffer) {
    if (audio) {
        audio.pause();
        audio = null;
    }

    const blob = new Blob([audioBuffer], { type: 'audio/mp3' });
    const url = URL.createObjectURL(blob);
    
    audio = new Audio(url);
    audio.volume = parseFloat(volumeSlider.value);
    
    audio.onplay = () => {
        updateStatus('正在播放...');
        updateButtonStates(true);
    };
    
    audio.onpause = () => {
        updateStatus('已暂停');
    };
    
    audio.onended = () => {
        updateStatus('播放完成');
        updateButtonStates(false);
        URL.revokeObjectURL(url);
    };
    
    audio.onerror = () => {
        updateStatus('播放失败');
        updateButtonStates(false);
        URL.revokeObjectURL(url);
    };
    
    audio.play();
}

function pauseAudio() {
    if (audio && !audio.paused) {
        audio.pause();
    }
}

function resumeAudio() {
    if (audio && audio.paused) {
        audio.play();
    }
}

function stopAudio() {
    if (audio) {
        audio.pause();
        audio.currentTime = 0;
        updateStatus('已停止');
        updateButtonStates(false);
    }
}

async function saveAudio() {
    const text = textInput.value.trim();
    if (!text) {
        updateStatus('请输入文本');
        return;
    }

    const voiceName = voiceSelect.value;
    if (!voiceName) {
        updateStatus('请选择语音');
        return;
    }

    updateStatus('正在生成并保存音频...');
    
    ipcRenderer.send('save-audio', {
        text: text,
        voiceName: voiceName,
        rate: parseFloat(rateSlider.value),
        pitch: parseFloat(pitchSlider.value)
    });
}

function openVoiceModal() {
    voiceModal.style.display = 'block';
    ipcRenderer.send('list-voices');
}

function closeVoiceModal() {
    voiceModal.style.display = 'none';
}

rateSlider.addEventListener('input', () => {
    rateValue.textContent = rateSlider.value;
});

pitchSlider.addEventListener('input', () => {
    pitchValue.textContent = pitchSlider.value;
});

volumeSlider.addEventListener('input', () => {
    volumeValue.textContent = volumeSlider.value;
    if (audio) {
        audio.volume = parseFloat(volumeSlider.value);
    }
});

playBtn.addEventListener('click', () => {
    if (!isPlaying) {
        speak();
    }
});

pauseBtn.addEventListener('click', () => {
    pauseAudio();
});

stopBtn.addEventListener('click', () => {
    stopAudio();
});

saveAudioBtn.addEventListener('click', saveAudio);

openFileBtn.addEventListener('click', () => {
    ipcRenderer.send('open-text-file');
});

manageVoicesBtn.addEventListener('click', openVoiceModal);
closeModalBtn.addEventListener('click', closeVoiceModal);

window.addEventListener('click', (e) => {
    if (e.target === voiceModal) {
        closeVoiceModal();
    }
});

addVoiceBtn.addEventListener('click', () => {
    const name = customVoiceName.value.trim();
    const shortName = customVoiceShortname.value.trim();
    const lang = customVoiceLang.value;

    if (!name || !shortName) {
        updateStatus('请填写完整信息');
        return;
    }

    ipcRenderer.send('add-custom-voice', {
        name: name,
        shortName: shortName,
        lang: lang
    });

    customVoiceName.value = '';
    customVoiceShortname.value = '';
});

ipcRenderer.on('voices-loaded', (event, voices) => {
    loadVoicesIntoSelect(voices);
    renderEdgeVoicesList();
    renderCustomVoicesList();
});

ipcRenderer.on('speech-generated', (event, { audioBuffer }) => {
    playAudio(audioBuffer);
});

ipcRenderer.on('speech-error', (event, error) => {
    updateStatus(`语音生成失败: ${error}`);
    updateButtonStates(false);
});

ipcRenderer.on('audio-saved', (event, filePath, error) => {
    if (error) {
        updateStatus(`保存失败: ${error}`);
    } else if (filePath) {
        updateStatus(`音频已保存: ${filePath}`);
    } else {
        updateStatus('保存已取消');
    }
});

ipcRenderer.on('custom-voice-added', (event, result) => {
    if (result.success) {
        updateStatus('自定义音源添加成功');
        ipcRenderer.send('list-voices');
    } else {
        updateStatus(`添加失败: ${result.error}`);
    }
});

ipcRenderer.on('custom-voice-removed', (event, result) => {
    if (result.success) {
        updateStatus('自定义音源已删除');
        ipcRenderer.send('list-voices');
    } else {
        updateStatus(`删除失败: ${result.error}`);
    }
});

ipcRenderer.on('text-file-opened', (event, data) => {
    if (data.content) {
        textInput.value = data.content;
        updateStatus(`已加载文件: ${data.filePath}`);
    }
});

ipcRenderer.send('list-voices');