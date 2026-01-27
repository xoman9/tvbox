# -*- coding: utf-8 -*-
import json
import sys
import re
from urllib.parse import urlparse

import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from requests import RequestException

sys.path.append('..')
from base.spider import Spider





class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass



    def homeContent(self, filter):
        result = {}
        class_type = {
            "电视剧": "2",
            "电影": "1",
            "VIP": "75099",
            "综艺": "4",
            "少儿": "210784",
            "动漫": "3",
            "教育": "211642"
        }
        classes = []
        filters = {}
        for k in class_type:
            classes.append({
                'type_name': k,
                'type_id': class_type[k]
            })

        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        pass



    def categoryContent(self, tid, pg, filter, extend):
        url = f"https://sou.pptv.com/category/typeid_{tid}_pn_{pg}_sortType_time"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'Referer': f'https://sou.pptv.com/category/typeid_{tid}'
        }

        response = requests.get(url, headers=headers)
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        video_list = []

        
        for li in soup.select('li.content'):
            
            vod_id = li.get('id', '')

            
            title_detail = li.select_one('.titleDetail')
            vod_name = title_detail.get_text(strip=True) if title_detail else ''

            
            img_tag = li.select_one('img')
            vod_pic = img_tag.get('src', '') if img_tag else ''

            
            score_span = li.select_one('.score')
            vod_remarks = ''.join(score_span.stripped_strings) if score_span else ''
            superscript = li.select_one('i.superscript.video')
            vip_em = superscript.select_one('em.video-vip') if superscript else None
            vip_text = vip_em.get_text(strip=True) if vip_em else vod_remarks
            
            if vip_text in [ "影视付费"]:
                continue  # 不加入列表
            
            video_list.append({
                'vod_id': vod_id,
                'vod_name': vod_name,
                'vod_pic': vod_pic,
                'vod_remarks': vip_text
            })
        result = {}
        result['list'] = video_list
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 30
        result['total'] = 999999
        return result



    def detailContent(self, ids):

        ids=ids[0]
        result = {}
        videos = []
        url = "https://epg.api.pptv.com/detail.api"
        params = {
            'ppi': '302c3532',
            'appId': 'pptv.web',
            'appPlt': 'web',
            'appVer': '1.0.0',
            'format': 'jsonp',
            'vid': ids,
            'series': '1',
            'contentType': 'preview',
            'ver': '4',
            'userLevel': '1',
            'cb': 'jsonp_1753969906635_25088'
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'Referer': 'https://v.pptv.com/',
        }

        response = requests.get(url, headers=headers, params=params)
        vod_play_url=''
        # 提取 JSONP 包裹的数据
        match = re.search(r'jsonp_\d+_\d+\((.*)\)', response.text)
        if match:
            json_data = json.loads(match.group(1))
            # print(json_data['v']['content'])

            if 'v' in json_data and 'video_list' in json_data['v']:
                playlink2 = json_data['v']['video_list'].get('playlink2', None)

                if isinstance(playlink2, list):  
                    for item in playlink2:
                        if isinstance(item, dict) and '_attributes' in item:
                            title = item['_attributes'].get('title', '')
                            vid = item['_attributes'].get('id', '')
                            vod_play_url += f"{title}${vid}#"

                elif isinstance(playlink2, dict) and playlink2:  
                    if '_attributes' in playlink2:
                        title = playlink2['_attributes'].get('title', '')
                        vid = playlink2['_attributes'].get('id', '')
                        vod_play_url += f"{title}${vid}#"

                
                if vod_play_url.endswith('#'):
                    vod_play_url = vod_play_url[:-1]


            video = {
                "vod_id": ids,
                "vod_name": json_data['v']['title'],
                "vod_actor": json_data['v']['act'],
                "vod_director":  json_data['v']['director'],
                "vod_content": json_data['v']['content'],
                "vod_year":json_data['v']['year'],
                "vod_area": json_data['v']['area'],
                "vod_play_from": "PP",
                "vod_play_url": vod_play_url
            }
            videos.append(video)
            result['list'] = videos
            return result
        else:
            raise ValueError("无法解析 JSONP 响应")


    def searchContent(self, key, quick, pg="1"):
        video_list = []
        url = f"https://sou.pptv.com/s_video?kw={key}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        }

        response = requests.get(url, headers=headers)
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.find_all('div', class_='positive-box clearfix')

        for div in divs:
            a_tag = div.find('a', class_='img-block')
            if not a_tag:
                continue

            ext_info = a_tag.get('ext_info', '{}')
            try:
                ext_data = json.loads(ext_info.replace("'", '"'))
                video_id = ext_data.get('video_id', '')
            except:
                video_id = ''

            title = a_tag.get('title', '')
            img_tag = a_tag.find('img', class_='cover')
            img_src = img_tag.get('src', '') if img_tag else ''
            if img_src and not img_src.startswith(('http://', 'https://')):
                img_src = f'https:{img_src}' if img_src.startswith('//') else f'https://{img_src}'


            span = a_tag.find('span')
            remarks = span.get_text(strip=True) if span else ''

            video_list.append({
                'vod_id': video_id,
                'vod_name': title,
                'vod_pic': img_src,
                'vod_remarks': remarks
            })
            result = {}
            result['list'] = video_list
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 30
            result['total'] = 999999
        return  result

    def playerContent(self, flag, id, vipFlags):
        url = f"https://sou.pptv.com/vvv/{id}.html"
        return {'jx': 1, 'parse': 1, 'url': url, 'header': ''}

    def localProxy(self, param):
        pass






