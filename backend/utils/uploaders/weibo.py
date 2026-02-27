#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博客户端
负责微博发布、Cookie验证、文件上传等操作
"""

import requests
import re
import json
import time
import random
import datetime
import os
import mimetypes
import hashlib
import logging
from time import time as timestamp
from typing import Optional, Dict, List


# 配置日志
logger = logging.getLogger(__name__)


class WeiboClient:
    """微博客户端类"""
    
    def __init__(self, cookie_str: str = None):
        """
        初始化微博客户端
        
        Args:
            cookie_str: 微博Cookie字符串
        """
        self.cookie_str = cookie_str or os.environ.get('WEIBO_COOKIE', '')
        self.session = requests.Session()
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://weibo.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        if self.cookie_str:
            self.headers['Cookie'] = self.cookie_str
        
        self.session.headers.update(self.headers)

    def calculate_file_md5(self, file_path: str) -> str:
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件的MD5哈希值
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def check_cookie_validity(self) -> bool:
        """
        检查Cookie是否有效
        
        Returns:
            Cookie是否有效
        """
        if not self.cookie_str:
            logger.error("未提供Cookie")
            return False
        
        # 从Cookie中提取SUB值
        sub_match = re.search(r'SUB=([^;]+)', self.cookie_str)
        if not sub_match:
            logger.warning("Cookie中没有SUB字段，可能已失效")
            return False

        # 从Cookie中提取过期时间
        alf_match = re.search(r'ALF=([^;]+)', self.cookie_str)
        if alf_match:
            try:
                alf_timestamp = int(alf_match.group(1))
                current_timestamp = int(time.time())
                
                if alf_timestamp <= current_timestamp:
                    logger.warning(f"Cookie已过期，过期时间: {datetime.datetime.fromtimestamp(alf_timestamp)}")
                    return False
                else:
                    expire_date = datetime.datetime.fromtimestamp(alf_timestamp)
                    logger.info(f"Cookie有效，过期时间: {expire_date}")
                    return True
            except ValueError:
                logger.warning("无法解析Cookie过期时间")
        
        # 如果没有ALF字段，尝试通过API验证
        return self._verify_cookie_by_api()

    def _verify_cookie_by_api(self) -> bool:
        """
        通过API验证Cookie有效性
        
        Returns:
            Cookie是否有效
        """
        try:
            # 尝试访问用户信息接口
            response = self.session.get(
                'https://weibo.com/ajax/user/info',
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') == 1:
                    logger.info("Cookie验证成功")
                    return True
            
            logger.warning(f"Cookie验证失败，状态码: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Cookie验证时出错: {e}")
            return False

    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传图片到微博
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            上传成功返回图片ID，失败返回None
        """
        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return None
        
        try:
            # 获取文件信息
            file_size = os.path.getsize(image_path)
            file_md5 = self.calculate_file_md5(image_path)
            mime_type, _ = mimetypes.guess_type(image_path)
            
            if not mime_type or not mime_type.startswith('image/'):
                logger.error(f"不支持的图片格式: {mime_type}")
                return None
            
            # 准备上传数据
            with open(image_path, 'rb') as f:
                files = {
                    'pic': (os.path.basename(image_path), f, mime_type)
                }
                
                data = {
                    'type': 'json',
                    'pic_id': '',
                    'category': 'page',
                    'location': 'page_100808_my_profile',
                    'nick': '',
                    'marks': '1',
                    'app': 'miniblog',
                    's': 'rdxt',
                    'pri': '0',
                    'file_source': '1'
                }
                
                # 上传图片
                response = self.session.post(
                    'https://picupload.weibo.com/interface/pic_upload.php',
                    files=files,
                    data=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == '0':
                        pic_id = result.get('data', {}).get('pic_id')
                        if pic_id:
                            logger.info(f"图片上传成功，ID: {pic_id}")
                            return pic_id
                    
                    logger.error(f"图片上传失败: {result}")
                else:
                    logger.error(f"图片上传请求失败，状态码: {response.status_code}")
                
        except Exception as e:
            logger.error(f"上传图片时出错: {e}")
        
        return None

    def post_weibo(self, content: str, image_paths: List[str] = None) -> bool:
        """
        发布微博
        
        Args:
            content: 微博内容
            image_paths: 图片文件路径列表
            
        Returns:
            发布是否成功
        """
        if not self.cookie_str:
            logger.error("未提供微博Cookie，无法发布")
            return False
        
        if not self.check_cookie_validity():
            logger.error("Cookie无效，无法发布微博")
            return False
        
        try:
            # 准备发布数据
            post_data = {
                'content': content,
                'pic_id': '',
                'pic_src': '',
                'style_type': '1',
                'location': 'v6_content_home',
                'appkey': '',
                'style_id': '2',
                'module': 'stissue',
                'pub_source': 'main_',
                'pub_type': 'dialog',
                'isPri': '0',
                'text': content,
                'pdetail': '',
                'rank': '0',
                'rankid': '',
                'module': 'stissue',
                'pub_source': 'main_'
            }
            
            # 如果有图片，先上传
            if image_paths:
                pic_ids = []
                for image_path in image_paths[:9]:  # 最多9张图片
                    pic_id = self.upload_image(image_path)
                    if pic_id:
                        pic_ids.append(pic_id)
                
                if pic_ids:
                    post_data['pic_id'] = ','.join(pic_ids)
                    logger.info(f"已上传 {len(pic_ids)} 张图片")
            
            # 发布微博
            response = self.session.post(
                'https://weibo.com/ajax/statuses/add',
                data=post_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok') == 1:
                    logger.info("微博发布成功！")
                    return True
                else:
                    error_msg = result.get('msg', '未知错误')
                    logger.error(f"微博发布失败: {error_msg}")
            else:
                logger.error(f"微博发布请求失败，状态码: {response.status_code}")
            
        except Exception as e:
            logger.error(f"发布微博时出错: {e}")
        
        return False

    def post_weibo_with_content_generator(self, content_type: str = "full", **kwargs) -> bool:
        """
        使用内容生成器发布微博
        
        Args:
            content_type: 内容类型 ("full" 或 "simple")
            **kwargs: 传递给内容生成器的参数
            
        Returns:
            发布是否成功
        """
        try:
            if content_type == "simple":
                content = self.content_generator.generate_simple_content(**kwargs)
            else:
                content = self.content_generator.generate_full_content(**kwargs)
            
            logger.info(f"生成的微博内容: {content[:100]}...")
            return self.post_weibo(content)
            
        except Exception as e:
            logger.error(f"使用内容生成器发布微博时出错: {e}")
            return False

    def post_weibo_with_hot_search_batch(self, batch_size: int = 5, delay_range: tuple = (300, 600)) -> Dict[str, int]:
        """
        批量发布热搜相关微博
        
        Args:
            batch_size: 批量发布数量
            delay_range: 发布间隔时间范围（秒）
            
        Returns:
            发布结果统计
        """
        results = {"success": 0, "failed": 0, "total": batch_size}
        
        try:
            # 获取热搜关键词
            hot_search = WeiboHotSearch()
            keywords = hot_search.get_positive_hot_search_keywords_with_hash()
            
            if not keywords:
                logger.warning("未获取到热搜关键词")
                keywords = [None] * batch_size
            
            for i in range(batch_size):
                try:
                    # 选择热搜关键词
                    keyword = keywords[i % len(keywords)] if keywords[0] else None
                    
                    # 生成并发布微博
                    success = self.post_weibo_with_content_generator(
                        content_type="full",
                        hot_search_keyword=keyword
                    )
                    
                    if success:
                        results["success"] += 1
                        logger.info(f"第 {i+1}/{batch_size} 条微博发布成功")
                    else:
                        results["failed"] += 1
                        logger.error(f"第 {i+1}/{batch_size} 条微博发布失败")
                    
                    # 随机延迟
                    if i < batch_size - 1:  # 最后一条不需要延迟
                        delay = random.randint(*delay_range)
                        logger.info(f"等待 {delay} 秒后发布下一条...")
                        time.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"发布第 {i+1} 条微博时出错: {e}")
                    results["failed"] += 1
            
            logger.info(f"批量发布完成: 成功 {results['success']} 条，失败 {results['failed']} 条")
            
        except Exception as e:
            logger.error(f"批量发布微博时出错: {e}")
        
        return results

    def get_user_info(self) -> Optional[Dict]:
        """
        获取当前用户信息
        
        Returns:
            用户信息字典或None
        """
        try:
            response = self.session.get(
                'https://weibo.com/ajax/user/info',
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') == 1:
                    return data.get('data')
            
            logger.error(f"获取用户信息失败，状态码: {response.status_code}")
            
        except Exception as e:
            logger.error(f"获取用户信息时出错: {e}")
        
        return None

    def get_weibo_list(self, count: int = 10) -> List[Dict]:
        """
        获取用户微博列表
        
        Args:
            count: 获取数量
            
        Returns:
            微博列表
        """
        try:
            response = self.session.get(
                f'https://weibo.com/ajax/statuses/mymblog?count={count}',
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') == 1:
                    return data.get('data', {}).get('list', [])
            
            logger.error(f"获取微博列表失败，状态码: {response.status_code}")
            
        except Exception as e:
            logger.error(f"获取微博列表时出错: {e}")
        
        return []


def main():
    """测试函数"""
    # 从环境变量获取Cookie
    cookie = 'SCF=Ak0EDU6vY1LVtshMiWQ-49zyR8rYIYGq4zsd2iLod1S_Z2y2_1wmO7wpeURl063XAxVCnF53h_oI73DISkATOW4.; SUB=_2A25Flq99DeRhGeBO7VMQ8SfKyD2IHXVm7a61rDV8PUNbmtANLW7CkW9NRfaQEQrILsEZxB9dg1uqJUiH9B7nklpV; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WhHGlGUFSMf1KezRUg8uHK15JpX5KzhUgL.Foq7So2peK.ce022dJLoIERLxK-LBo5L12qLxK-LBo5L12qLxK-LBo5L12qLxKML1h2LBo5LxKML1h2LBoWs; ALF=02_1757047853; _s_tentry=weibo.com; Apache=1101442547905.8975.1754528853478; SINAGLOBAL=1101442547905.8975.1754528853478; ULV=1754528853480:1:1:1:1101442547905.8975.1754528853478:'
    if not cookie:
        print("请设置WEIBO_COOKIE环境变量")
        return
    
    # 创建微博客户端
    client = WeiboClient(cookie)
    
    # 检查Cookie有效性
    print("=== 检查Cookie有效性 ===")
    is_valid = client.check_cookie_validity()
    print(f"Cookie有效性: {is_valid}")
    
    if not is_valid:
        print("Cookie无效，无法继续测试")
        return
    
    # 获取用户信息
    print("\n=== 获取用户信息 ===")
    user_info = client.get_user_info()
    if user_info:
        print(f"用户昵称: {user_info.get('screen_name')}")
        print(f"用户ID: {user_info.get('id')}")
    
    # 测试内容生成和发布
    print("\n=== 测试微博发布 ===")
    print("注意：这将实际发布微博，请确认是否继续 (y/N):")
    confirm = input().strip().lower()
    
    if confirm == 'y':
        success = client.post_weibo_with_content_generator("full")
        print(f"微博发布结果: {success}")
    else:
        print("已取消微博发布测试")


if __name__ == "__main__":
    main()