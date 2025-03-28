from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import tempfile
import uuid
import traceback
from pydub import AudioSegment
import time
from werkzeug.utils import secure_filename
import io
import sys
import json
from vosk import Model, KaldiRecognizer
import wave
import soundfile as sf
import numpy as np

app = Flask(__name__, static_url_path='', static_folder='.')
# 配置CORS，增加超时时间
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "max_age": 3600
    }
})

# 配置上传文件大小限制（设置为50MB）
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
# 增加请求超时时间
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 创建临时文件夹
TEMP_DIR = tempfile.gettempdir()
UPLOAD_FOLDER = os.path.join(TEMP_DIR, 'audio_extractor')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 增加缓冲区大小
BUFFER_SIZE = 10 * 1024 * 1024  # 10MB buffer

# Vosk模型路径
VOSK_MODEL_PATH_ZH = "vosk-model-cn-0.22"  # 中文模型
VOSK_MODEL_PATH_EN = "vosk-model-en-us-0.22"  # 英文模型

def get_vosk_model(language):
    """获取对应语言的Vosk模型"""
    model_path = VOSK_MODEL_PATH_ZH if language == 'zh' else VOSK_MODEL_PATH_EN
    if not os.path.exists(model_path):
        return None
    return Model(model_path)

def preprocess_audio(audio_segment):
    """音频预处理以提高识别质量"""
    # 标准化音量
    audio_segment = audio_segment.normalize()
    
    # 降噪处理
    audio_segment = audio_segment.low_pass_filter(3000)
    
    # 调整采样率为16kHz
    audio_segment = audio_segment.set_frame_rate(16000)
    
    # 转换为单声道
    audio_segment = audio_segment.set_channels(1)
    
    # 调整音频速率（稍微放慢可能提高识别率）
    audio_segment = audio_segment._spawn(audio_segment.raw_data, overrides={
        "frame_rate": int(audio_segment.frame_rate * 0.95)
    })
    
    return audio_segment

def convert_to_wav(input_path, max_retries=3):
    """将音频转换为WAV格式，带有预处理"""
    for attempt in range(max_retries):
        try:
            print(f"开始转换音频为WAV格式，尝试 {attempt + 1}/{max_retries}")
            print(f"输入文件: {input_path}")
            
            # 验证输入文件
            if not os.path.exists(input_path):
                raise Exception(f"输入文件不存在: {input_path}")
            
            # 生成临时WAV文件路径
            wav_path = os.path.splitext(input_path)[0] + '.wav'
            print(f"WAV输出路径: {wav_path}")
            
            # 使用pydub转换音频
            audio = AudioSegment.from_file(input_path)
            print(f"原始音频长度: {len(audio)} ms")
            
            if len(audio) == 0:
                raise Exception("音频长度为0")
            
            # 应用音频预处理
            print("正在进行音频预处理...")
            audio = preprocess_audio(audio)
            
            # 导出为WAV格式
            audio.export(wav_path, format='wav')
            
            # 验证生成的WAV文件
            if not os.path.exists(wav_path):
                raise Exception("WAV文件未生成")
            
            wav_size = os.path.getsize(wav_path)
            print(f"生成的WAV文件大小: {wav_size} bytes")
            if wav_size == 0:
                raise Exception("生成的WAV文件大小为0")
            
            print("WAV转换完成")
            return wav_path
            
        except Exception as e:
            print(f"WAV转换失败，尝试 {attempt + 1}/{max_retries}: {str(e)}")
            traceback.print_exc()
            
            # 清理可能的不完整文件
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except:
                pass
                
            if attempt == max_retries - 1:
                raise Exception(f"WAV转换失败: {str(e)}")
            
            time.sleep(2)  # 重试前等待
    
    return None

def extract_audio_from_video(video_path, audio_path, max_retries=3):
    """从视频中提取音频，带有重试机制和验证"""
    for attempt in range(max_retries):
        try:
            print(f"开始提取音频，尝试 {attempt + 1}/{max_retries}")
            print(f"视频文件路径: {video_path}")
            print(f"音频输出路径: {audio_path}")
            
            # 验证视频文件
            if not os.path.exists(video_path):
                raise Exception(f"视频文件不存在: {video_path}")
            
            # 检查视频文件大小
            video_size = os.path.getsize(video_path)
            print(f"视频文件大小: {video_size} bytes")
            if video_size == 0:
                raise Exception("视频文件大小为0")
            
            # 使用moviepy提取音频
            video = VideoFileClip(video_path)
            if video.audio is None:
                raise Exception("视频文件没有音轨")
                
            print("成功加载视频文件，开始提取音频...")
            audio = video.audio
            
            # 保存音频
            audio.write_audiofile(audio_path, 
                                codec='mp3',
                                bitrate='192k',
                                verbose=True,
                                logger=None)
            
            # 验证生成的音频文件
            if not os.path.exists(audio_path):
                raise Exception("音频文件未生成")
            
            audio_size = os.path.getsize(audio_path)
            print(f"生成的音频文件大小: {audio_size} bytes")
            if audio_size == 0:
                raise Exception("生成的音频文件大小为0")
            
            # 关闭视频对象
            video.close()
            
            print("音频提取完成")
            return True
            
        except Exception as e:
            print(f"音频提取失败，尝试 {attempt + 1}/{max_retries}: {str(e)}")
            traceback.print_exc()
            
            # 清理可能的不完整文件
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except:
                pass
                
            if attempt == max_retries - 1:
                raise Exception(f"音频提取失败: {str(e)}")
            
            time.sleep(2)  # 重试前等待
            
    return False

def verify_audio_file(file_path, max_retries=3):
    """验证音频文件是否可以正常读取"""
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                if len(content) > 1024:  # 确保文件大小至少大于1KB
                    return True
        except Exception as e:
            print(f"验证音频文件失败，尝试重试 {attempt + 1}/{max_retries}: {str(e)}")
            time.sleep(2)  # 增加等待时间
    return False

def read_in_chunks(file_path, chunk_size=BUFFER_SIZE):
    """分块读取文件"""
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            yield chunk

def safe_file_save(file, path, max_retries=3):
    """安全地保存文件，带有重试机制"""
    for attempt in range(max_retries):
        try:
            file.save(path)
            # 验证文件是否完整保存
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return True
            else:
                print(f"文件保存不完整，尝试重试 {attempt + 1}/{max_retries}")
        except Exception as e:
            print(f"保存文件失败，尝试重试 {attempt + 1}/{max_retries}: {str(e)}")
            time.sleep(1)  # 等待1秒后重试
    return False

def safe_audio_recognition(wav_path, language, max_retries=3):
    """使用多个引擎进行语音识别"""
    for attempt in range(max_retries):
        try:
            if not verify_audio_file(wav_path):
                raise Exception("音频文件验证失败")

            print(f"开始语音识别，尝试 {attempt + 1}/{max_retries}")
            
            # 获取Vosk模型
            model = get_vosk_model(language)
            if model is None:
                return "请先下载对应的语音模型文件"
            
            try:
                # 分割音频为较短的片段（每段30秒）
                audio = AudioSegment.from_wav(wav_path)
                segment_length = 30 * 1000  # 30秒
                segments = []
                
                for i in range(0, len(audio), segment_length):
                    segment = audio[i:i + segment_length]
                    segment_path = f"{wav_path}.segment_{i}.wav"
                    segment.export(segment_path, format='wav')
                    segments.append(segment_path)
                
                results = []
                
                # 处理每个片段
                for segment_path in segments:
                    # 读取WAV文件
                    wf = wave.open(segment_path, "rb")
                    
                    # 创建识别器
                    rec = KaldiRecognizer(model, wf.getframerate())
                    rec.SetWords(True)
                    
                    # 读取音频数据
                    while True:
                        data = wf.readframes(4000)
                        if len(data) == 0:
                            break
                        if rec.AcceptWaveform(data):
                            part_result = json.loads(rec.Result())
                            if 'text' in part_result and part_result['text'].strip():
                                results.append(part_result['text'])
                    
                    # 获取最后的结果
                    part_result = json.loads(rec.FinalResult())
                    if 'text' in part_result and part_result['text'].strip():
                        results.append(part_result['text'])
                    
                    # 关闭文件
                    wf.close()
                    
                    # 清理临时文件
                    try:
                        os.remove(segment_path)
                    except:
                        pass
                
                if not results:
                    return "未能识别出任何文字"
                    
                # 合并所有结果
                return ' '.join(results)
                
            except Exception as e:
                print(f"Vosk识别失败: {str(e)}")
                traceback.print_exc()
                if attempt == max_retries - 1:
                    return f"语音识别失败: {str(e)}"
                
        except Exception as e:
            print(f"音频识别出错，尝试重试 {attempt + 1}/{max_retries}: {str(e)}")
            traceback.print_exc()
            if attempt == max_retries - 1:
                raise e
        
        print(f"等待 {attempt + 1} 秒后重试...")
        time.sleep(attempt + 1)  # 递增等待时间
    
    return "音频识别失败，已达到最大重试次数"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/css/<path:filename>')
def css(filename):
    return send_from_directory('css', filename)

@app.route('/js/<path:filename>')
def js(filename):
    return send_from_directory('js', filename)

@app.route('/api/process', methods=['POST', 'OPTIONS'])
def process_video():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        print("接收到处理请求")
        
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            return jsonify({'error': '不支持的文件格式。请上传MP4、AVI、MOV或MKV格式的视频'}), 400

        print(f"文件名: {file.filename}")

        extract_audio = request.form.get('extractAudio', 'true').lower() == 'true'
        transcribe_text = request.form.get('transcribeText', 'true').lower() == 'true'
        audio_format = request.form.get('audioFormat', 'mp3')
        transcribe_language = request.form.get('transcribeLanguage', 'zh')

        print(f"处理选项: 提取音频={extract_audio}, 转写文字={transcribe_text}, 格式={audio_format}, 语言={transcribe_language}")

        unique_id = str(uuid.uuid4())
        video_path = os.path.join(UPLOAD_FOLDER, f'{unique_id}_video{os.path.splitext(file.filename)[1]}')
        audio_path = os.path.join(UPLOAD_FOLDER, f'{unique_id}_audio.{audio_format}')

        # 保存上传的视频文件
        print("保存视频文件...")
        if not safe_file_save(file, video_path):
            return jsonify({'error': '文件保存失败'}), 500

        # 验证保存的视频文件
        video_size = os.path.getsize(video_path)
        print(f"保存的视频文件大小: {video_size} bytes")
        if video_size == 0:
            return jsonify({'error': '上传的视频文件为空'}), 400

        transcribed_text = ""
        audio_url = None

        try:
            if extract_audio:
                print("开始提取音频")
                if not extract_audio_from_video(video_path, audio_path):
                    return jsonify({'error': '音频提取失败'}), 500
                print("音频提取完成")
                audio_url = f'/api/audio/{os.path.basename(audio_path)}'

                if transcribe_text:
                    print("开始转写文字")
                    try:
                        wav_path = convert_to_wav(audio_path)
                        if wav_path is None:
                            raise Exception("WAV转换失败")
                        
                        print(f"WAV文件路径: {wav_path}")
                        transcribed_text = safe_audio_recognition(wav_path, transcribe_language)
                        print("文字转写完成")

                        try:
                            os.remove(wav_path)
                        except:
                            pass
                    except Exception as e:
                        print(f"转写过程出错: {str(e)}")
                        traceback.print_exc()
                        transcribed_text = f"转写失败: {str(e)}"

        finally:
            # 清理视频文件
            try:
                os.remove(video_path)
            except:
                pass

        response = {
            'success': True,
            'audioUrl': audio_url,
            'transcribedText': transcribed_text
        }

        print("处理完成，返回结果")
        return jsonify(response)

    except Exception as e:
        error_msg = f"处理错误: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({
            'error': str(e),
            'details': traceback.format_exc()
        }), 500

@app.route('/api/audio/<filename>')
def get_audio(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
            
        # 使用流式传输发送文件
        def generate():
            for chunk in read_in_chunks(file_path):
                yield chunk

        response = app.response_class(
            generate(),
            mimetype='audio/mpeg',
            direct_passthrough=True
        )
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
    except Exception as e:
        print(f"获取音频错误: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    print("服务器启动在 http://localhost:8000")  # 调试日志
    app.run(debug=True, port=8000, threaded=True) 