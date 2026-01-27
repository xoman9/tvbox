# -*- coding: utf-8 -*-
import json
import sys
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
sys.path.append('..')
from base.spider import Spider
import hashlib
import time

MOBILE_UA = "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36"
host='https://m.jiabaide.cn'

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

    def getkjson(self,url):
        global MOBILE_UA
        t = str(int(time.time() * 1000))
        query = url.split('?')[1]
        sign_raw = f"{query}&key=cb808529bae6b6be45ecfab29a4889bc&t={t}"
        sign_raw = sign_raw.lstrip('&')
        md5_hash = hashlib.md5(sign_raw.encode('utf-8')).hexdigest()
        sha1_hash = hashlib.sha1(md5_hash.encode('utf-8')).hexdigest()

        headers = {
            'User-Agent': MOBILE_UA,
            't': t,
            'sign': sha1_hash
        }

        response = requests.get(url, headers=headers)
        return response.json()

    def homeContent(self, filter):
        result = {}
        class_type = {
            "电影": "1",
            "电视剧": "2",
            "综艺": "3",
            "动漫": "4"


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

        global data
        url = "https://m.jiabaide.cn/api/mw-movie/anonymous/home/hotSearch?"
        try:
            data =self. getkjson(url)
        except Exception as e:
            print(f"请求失败: {e}")

        videoList = []
        for i in data['data']:
            videoList.append({
                'vod_id': i['vodId'] ,
                'vod_name': i['vodName'],
                'vod_pic': i['vodPic'],
                'vod_remarks': i['vodRemarks']
            })
        result = {}
        result['list'] = videoList

        return result

    def categoryContent(self, tid, pg, filter, extend):
        global host

        params = {
            "area": extend.get('area', ''),
            "filterStatus": "1",
            "lang": extend.get('lang', ''),
            "pageNum": pg,
            "pageSize": "30",
            "sort": extend.get('sort', '1'),
            "sortBy": "1",
            "type": extend.get('type', ''),
            "type1": tid,
            "v_class": extend.get('v_class', ''),
            "year": extend.get('year', '')
        }

        url = f"{host}/api/mw-movie/anonymous/video/list?{self.js(params)}"
        try:
            data = self.getkjson(url)
            print(data)
        except Exception as e:
            print(f"请求失败: {e}")

        videoList = []
        for i in data['data']['list']:
            videoList.append({
                'vod_id': i['vodId'],
                'vod_name': i['vodName'],
                'vod_pic': i['vodPic'],
                'vod_remarks': i.get('vodRemarks') or i.get('vodVersion') or i.get('vodArea')
            })
        result = {}
        result['list'] = videoList
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def js(self, param):
        return '&'.join(f"{k}={v}" for k, v in param.items())
    def detailContent(self, ids):
        global detailContent
        url = f"{host}/api/mw-movie/anonymous/video/detail?id={ids[0]}"
        try:
            detailContent = self.getkjson(url)
            print(detailContent)
        except Exception as e:
            print(f"请求失败: {e}")

        result = {}
        videos = []
        vod_id= detailContent["data"]["vodId"]
        video = {
            "vod_id": vod_id,
            "vod_name": detailContent["data"]["vodName"],
            "vod_actor": detailContent["data"]["vodActor"],
            "vod_director": detailContent["data"]["vodDirector"],
            "vod_content": detailContent["data"]["vodContent"],
            "vod_year": detailContent["data"]["vodYear"],
            "vod_area": detailContent["data"]["vodArea"],
            "vod_play_from": '冠军',
            "vod_play_url": ''
        }

        play_url = ''
        for index, i in enumerate(detailContent["data"]["episodeList"]):
            play_url += f"{index + 1}$https://m.jiabaide.cn/JP-{detailContent['data']['vodId']}-{i['nid']}#"
        play_url = play_url[:-1]
        video['vod_play_url'] = play_url
        videos.append(video)
        result['list'] = videos

        return result

    def searchContent(self, key, quick, pg="1"):
        params = {
            "keyword": key,
            "pageNum": pg,
            "pageSize": "8",
            "sourceCode": "1"
        }

        url = f"{host}/api/mw-movie/anonymous/video/searchByWord?{self.js(params)}"
        try:
            data = self.getkjson(url)
            # print(data)
        except Exception as e:
            print(f"请求失败: {e}")

        videoList = []
        for i in data['data']['result']['list']:
            videoList.append({
                'vod_id': i['vodId'],
                'vod_name': i['vodName'],
                'vod_pic': i['vodPic'],
                'vod_remarks': i.get('vodRemarks') or i.get('vodVersion') or i.get('vodArea')
            })
        result = {}
        result['list'] = videoList
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def playerContent(self, flag, id, vipFlags):
        return {'jx': 1, 'parse': 1, 'url': id, 'header': ''}

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None