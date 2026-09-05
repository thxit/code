import requests
from bs4 import BeautifulSoup
import json
import time

# 注意：微信反爬严格，此示例仅作学习参考，实际使用需遵守微信平台规则

def get_articles(account_id, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Cookie': cookie,
        'Referer': f'https://mp.weixin.qq.com/mp/homepage?__biz={account_id}&hid=1&sn=xxx'
    }

    article_list = []
    offset = 0
    while True:
        url = f'https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum_article_list&__biz={account_id}&scene=1&album_id=xxx&count=10&offset={offset}&f=json'
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            if data.get('base_resp', {}).get('ret') != 0:
                print('请求失败，可能Cookie过期或权限不足')
                break
            articles = data.get('list', [])
            if not articles:
                break
            for article in articles:
                article_info = {
                    'title': article.get('title'),
                    'url': article.get('link'),
                    'publish_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(article.get('create_time'))),
                    'content': get_article_content(article.get('link'), headers)
                }
                article_list.append(article_info)
            offset += 10
            time.sleep(2)  # 降低请求频率避免被封
        except Exception as e:
            print(f'抓取异常：{str(e)}')
            break
    return article_list

def get_article_content(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # 显式指定UTF-8编码解决中文乱码问题
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        content_div = soup.find('div', id='js_content')
        return content_div.get_text(strip=True) if content_div else ''
    except Exception as e:
        print(f'获取文章内容失败：{str(e)}')
        return ''

def save_articles(articles, filename='wechat_articles.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f'文章已保存至{filename}')

if __name__ == '__main__':
    # 使用说明：
    # 1. 登录微信公众平台，从浏览器获取Cookie（包含token等关键信息）
    # 2. 替换为目标公众号的__biz参数（可从公众号主页URL获取）
    # 3. 注意遵守微信开发者协议，勿用于非法爬取
    ACCOUNT_ID = '替换为目标公众号的__biz'
    COOKIE = '替换为你的浏览器Cookie'

    articles = get_articles(ACCOUNT_ID, COOKIE)
    if articles:
        save_articles(articles)
    else:
        print('未获取到文章数据')