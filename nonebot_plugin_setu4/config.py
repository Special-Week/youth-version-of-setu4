import os
import json
import nonebot

# 色图cd容器
cd_dir: dict = {}

# setu cd,可在env设置,默认20s,类型int
try:
    cdTime: int = nonebot.get_driver().config.setu_cd
except:
    cdTime: int = 20


# 撤回时间,可在env设置,默认100s,类型int
try:
    withdraw_time: int = nonebot.get_driver().config.setu_withdraw_time
except:
    withdraw_time: int = 100

# 一次最大多少张图片,可在env设置,默认10张,类型int
try:
    max_num: int = nonebot.get_driver().config.setu_max_num
except:
    max_num: int = 10


# 读取r18list
if os.path.exists('data/youth-version-of-setu4/config.json'):
    with open('data/youth-version-of-setu4/config.json', 'r', encoding="utf-8") as fp:
        config_json = json.load(fp)
else:  # 不存在则创建
    if not os.path.exists('data/youth-version-of-setu4'):
        os.makedirs('data/youth-version-of-setu4')
    config_json = {
        "r18list": [],
        "banlist": [],
        "setu_proxy":"i.pixiv.re"
        }
    with open('data/youth-version-of-setu4/config.json', 'w', encoding="utf-8") as fp:
        json.dump(config_json, fp, ensure_ascii=False)
"""
json结构:
{
    "r18list": [
        "123456789",
        "987654321"
    ],
    "banlist": [
        "123456789",
        "987654321"
    ],
    "setu_proxy":"i.pixiv.re"
}
"""

def write_configjson():
    """写入json"""
    with open('data/youth-version-of-setu4/config.json', 'w', encoding="utf-8") as fp:
        json.dump(config_json, fp, ensure_ascii=False)

def ReadProxy():
    """读取代理"""
    return config_json["setu_proxy"]

def WriteProxy(proxy):
    """写入代理"""
    config_json["setu_proxy"] = proxy
    write_configjson()

# r18允许的列表["123456789","987654321"]
r18list = config_json["r18list"]
banlist = config_json["banlist"]



def to_json(msg, name: str, uin: str) -> dict:
    """转换为dict, 转发消息用"""
    return {
        'type': 'node',
        'data': {
            'name': name,
            'uin': uin,
            'content': msg
        }
    }
