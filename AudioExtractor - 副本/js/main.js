// DOM 元素
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const processSection = document.getElementById('processSection');
const videoPreview = document.getElementById('videoPreview');
const processBtn = document.getElementById('processBtn');
const resultSection = document.getElementById('resultSection');
const progressModal = document.getElementById('progressModal');
const progressText = document.querySelector('.progress-text');
const audioPlayer = document.getElementById('audioPlayer');
const transcribedText = document.getElementById('transcribedText');
const downloadAudioBtn = document.getElementById('downloadAudio');
const downloadTextBtn = document.getElementById('downloadText');

// 当前处理的文件
let currentFile = null;
let currentAudioUrl = null;

// 拖放处理
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = 'var(--primary-color)';
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.style.borderColor = 'var(--border-color)';
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = 'var(--border-color)';
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
        handleFile(file);
    }
});

// 文件选择处理
uploadBtn.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
});

// 处理选择的文件
function handleFile(file) {
    currentFile = file;
    
    // 显示视频预览
    const videoUrl = URL.createObjectURL(file);
    videoPreview.src = videoUrl;
    
    // 显示处理区域
    processSection.style.display = 'block';
    resultSection.style.display = 'none';
}

// 处理按钮点击
processBtn.addEventListener('click', async () => {
    if (!currentFile) {
        alert('请先选择视频文件');
        return;
    }
    
    const extractAudio = document.getElementById('extractAudio').checked;
    const transcribeText = document.getElementById('transcribeText').checked;
    const audioFormat = document.getElementById('audioFormat').value;
    const transcribeLanguage = document.getElementById('transcribeLanguage').value;
    
    // 显示进度模态框
    progressModal.style.display = 'flex';
    
    try {
        // 创建表单数据
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('extractAudio', extractAudio);
        formData.append('transcribeText', transcribeText);
        formData.append('audioFormat', audioFormat);
        formData.append('transcribeLanguage', transcribeLanguage);

        console.log('开始发送请求...');  // 调试日志
        
        // 发送请求到后端
        const response = await fetch('http://localhost:8000/api/process', {
            method: 'POST',
            body: formData,
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'Accept': 'application/json'
            }
        });

        console.log('收到响应:', response.status);  // 调试日志

        if (!response.ok) {
            const errorData = await response.json();
            console.error('错误详情:', errorData);  // 调试日志
            throw new Error(errorData.error || '处理失败');
        }

        const data = await response.json();
        console.log('处理结果:', data);  // 调试日志

        // 显示结果
        resultSection.style.display = 'block';
        
        // 更新音频播放器
        if (data.audioUrl) {
            currentAudioUrl = `http://localhost:8000${data.audioUrl}`;
            audioPlayer.src = currentAudioUrl;
        }
        
        // 更新转写文本
        if (data.transcribedText) {
            transcribedText.value = data.transcribedText;
        }
        
    } catch (error) {
        console.error('处理失败:', error);
        alert(`处理失败: ${error.message || '请重试'}`);
    } finally {
        progressModal.style.display = 'none';
    }
});

// 标签切换
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // 移除所有活动状态
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // 添加当前活动状态
        btn.classList.add('active');
        document.getElementById(`${btn.dataset.tab}Tab`).classList.add('active');
    });
});

// 下载音频
downloadAudioBtn.addEventListener('click', () => {
    if (currentAudioUrl) {
        window.open(currentAudioUrl, '_blank');
    } else {
        alert('没有可下载的音频文件');
    }
});

// 下载文本
downloadTextBtn.addEventListener('click', () => {
    const text = transcribedText.value;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'transcribed_text.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}); 