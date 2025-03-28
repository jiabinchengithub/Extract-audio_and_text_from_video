import os
import requests
import zipfile
from tqdm import tqdm
import sys

def download_file(url, filename):
    """下载文件并显示进度条"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)

def extract_zip(zip_path, extract_path):
    """解压ZIP文件并显示进度"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        total_files = len(zip_ref.filelist)
        print(f"\n正在解压 {zip_path} 到 {extract_path}")
        for i, file in enumerate(zip_ref.filelist, 1):
            zip_ref.extract(file, extract_path)
            print(f"解压进度: {i}/{total_files}", end='\r')
    print("\n解压完成!")

def download_and_setup_models():
    """下载并设置Vosk语音模型"""
    models = {
        'vosk-model-cn-0.22': 'https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip',
        'vosk-model-en-us-0.22': 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip'
    }
    
    for model_name, url in models.items():
        zip_file = f"{model_name}.zip"
        
        # 检查模型文件夹是否已存在
        if os.path.exists(model_name):
            print(f"\n{model_name} 已存在，跳过下载...")
            continue
            
        print(f"\n开始下载 {model_name}...")
        try:
            # 下载模型
            download_file(url, zip_file)
            
            # 解压模型
            extract_zip(zip_file, '.')
            
            # 删除ZIP文件
            os.remove(zip_file)
            print(f"{model_name} 设置完成!")
            
        except Exception as e:
            print(f"\n下载或解压 {model_name} 时出错: {str(e)}")
            if os.path.exists(zip_file):
                os.remove(zip_file)
            sys.exit(1)

if __name__ == '__main__':
    print("开始下载语音模型...")
    download_and_setup_models()
    print("\n所有模型下载完成!") 