import requests
from bs4 import BeautifulSoup
import os
import re

# 定义请求头，模拟浏览器访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://www.zhihu.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}


def get_answer_content(answer_url):
    try:
        response = requests.get(answer_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # 提取答案内容
        content = soup.find('div', class_='RichContent-inner')
        if content:
            return content.get_text(strip=True)
        else:
            return '未找到答案内容'
    except Exception as e:
        print(f'请求出错: {e}')
        return ''


def download_images(answer_url, save_dir):
    try:
        response = requests.get(answer_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # 查找所有图片标签
        img_tags = soup.find_all('img', class_='content_image')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        for index, img in enumerate(img_tags):
            img_url = img.get('src')
            if img_url:
                try:
                    img_response = requests.get(img_url, headers=headers)
                    img_response.raise_for_status()
                    file_ext = os.path.splitext(img_url)[1]
                    file_name = os.path.join(save_dir, f'image_{index}{file_ext}')
                    with open(file_name, 'wb') as f:
                        f.write(img_response.content)
                    print(f'图片 {file_name} 下载完成')
                except Exception as e:
                    print(f'下载图片 {img_url} 出错: {e}')
    except Exception as e:
        print(f'请求出错: {e}')


if __name__ == '__main__':
    answer_url = input('请输入知乎答案的链接: ')
    answer_content = get_answer_content(answer_url)
    print('答案内容:', answer_content)
    save_dir = 'zhihu_images'
    download_images(answer_url, save_dir)