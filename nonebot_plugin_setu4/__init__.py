import random
import asyncio
import nonebot
import platform
from re import I, sub
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot import on_command, on_regex
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg, ArgPlainText
from nonebot.adapters.onebot.v11.permission import GROUP_OWNER, GROUP_ADMIN
from nonebot.adapters.onebot.v11 import (GROUP, PRIVATE_FRIEND, Bot,
                                         GroupMessageEvent, Message,
                                         MessageEvent, MessageSegment,
                                         PrivateMessageEvent)

from .config import *
from .get_data import get_setu
from .setu_message import setu_sendcd, setu_sendmessage

# 正则部分
setu = on_regex(
    r"^(setu|色图|涩图|想色色|来份色色|来份色图|想涩涩|多来点|来点色图|来张setu|来张色图|来点色色|色色|涩涩)\s?([x|✖️|×|X|*]?\d+[张|个|份]?)?\s?(r18)?\s?(.*)?",
    flags=I,
    permission=PRIVATE_FRIEND | GROUP,
    priority=10,
    block=True
)


# 响应器处理操作
@setu.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    args = list(state["_matched_groups"])       # 获取正则匹配到的参数
    r18flag = args[2]                    # 获取r18参数
    key = args[3]                 # 获取关键词参数
    key = sub('[\'\"]', '', key)  # 去掉引号防止sql注入
    num = args[1]          # 获取数量参数
    num = int(sub(r"[张|个|份|x|✖️|×|X|*]", "", num)) if num else 1

    qid = event.get_user_id()
    sid = event.get_session_id()
    # 判断该群聊setu功能是否被禁用
    for session_id in banlist:
        if str(session_id) in sid:
            await setu.finish("涩图功能已在此会话中禁用！")

    if num > max_num or num < 1:
        await setu.finish(f"数量需要在1-{max_num}之间")

    try:
        cd = event.time - cd_dir[qid]
    except KeyError:
        cd = cdTime + 1

    # 先判断r18flag和私聊是不是都是True进行赋值
    r18 = True if (isinstance(event, PrivateMessageEvent)
                   and r18flag) else False
    # 如果r18是false的话在进行r18list判断
    if not r18:
        for groubnumber in r18list:
            if groubnumber in sid:
                r18 = (True if (r18flag) else False)

    # key按照空格切割为数组, 用于多关键词搜索, 并且把数组中的空元素去掉
    key = key.split(" ")
    key = [word.strip() for word in key if word.strip()]

    if key == []:
        flagLog = f"\nR18 == {str(r18)}\nkeyword == NULL\nnum == {num}\n"
    else:
        flagLog = f"\nR18 == {str(r18)}\nkeyword == {key}\nnum == {num}\n"
    logger.info(f"key = {key}\tr18 = {r18}\tnum = {num}")       # 控制台输出

    # cd判断,superusers无视cd
    if (
        cd > cdTime
        or event.get_user_id() in nonebot.get_driver().config.superusers
    ):
        # 色图图片质量, 如果num为3-6质量为70,如果num为7-max质量为50,其余为95(图片质量太高发起来太费时间了)
        # 注:quality值95为原图
        if num >= 3 and num <= 6:
            quality = 70
        elif num >= 7:
            quality = 50
        else:
            quality = 95

        if num >= 3:
            await setu.send(f"由于数量过多请等待\n当前图片质量为{quality}\n3-6:quality = 70\n7-{max_num}:quality = 50")
        # 记录cd
        cd_dir.update({qid: event.time})
        # data是数组套娃, 数组中的每个元素内容为: [图片, 信息, True/False, url]
        try:
            data = await get_setu(key, r18, num, quality)
        except Exception as e:
            await setu.finish(f"Error: " + str(e))

        # 发送的消息列表
        message_list = []
        for pic in data:
            # 如果状态为True,说明图片拿到了
            if pic[2]:
                message = f"{random.choice(setu_sendmessage)}{flagLog}" + \
                    Message(pic[1]) + MessageSegment.image(pic[0])
                flagLog = ""
                message_list.append(message)
            # 状态为false的消息,图片没拿到
            else:
                message = pic[0] + pic[1]
                message_list.append(message)

        # 为后面撤回消息做准备
        setu_msg_id = []
        # 尝试发送
        try:
            if isinstance(event, PrivateMessageEvent):
                # 私聊直接发送
                for msg in message_list:
                    setu_msg_id.append((await setu.send(msg))['message_id'])
            elif isinstance(event, GroupMessageEvent):
                # 群聊以转发消息的方式发送
                msgs = [to_json(msg, "setu-bot", bot.self_id)
                        for msg in message_list]
                setu_msg_id.append((await bot.call_api('send_group_forward_msg', group_id=event.group_id, messages=msgs))['message_id'])

        # 发送失败
        except ActionFailed as e:
            # logger以及移除cd
            logger.warning(e)
            cd_dir.pop(qid)
            await setu.finish(
                message=Message(f"消息被风控了捏，图发不出来，请尽量减少发送的图片数量"),
                at_sender=True,
            )

    # cd还没过的情况
    else:
        time_last = cdTime - cd
        hours, minutes, seconds = 0, 0, 0
        if time_last >= 60:
            minutes, seconds = divmod(time_last, 60)
            hours, minutes = divmod(minutes, 60)
        else:
            seconds = time_last
        cd_msg = f"{str(hours) + '小时' if hours else ''}{str(minutes) + '分钟' if minutes else ''}{str(seconds) + '秒' if seconds else ''}"

        await setu.send(f"{random.choice(setu_sendcd)} 你的CD还有{cd_msg}", at_sender=True)

     # 自动撤回涩图
    if withdraw_time != 0:
        try:
            await asyncio.sleep(withdraw_time)
            for msg_id in setu_msg_id:
                await bot.delete_msg(message_id=msg_id)
        except:
            pass


# r18列表添加用的,权限SUPERSUSER
addr18list = on_command("add_r18", permission=SUPERUSER,
                        block=True, priority=10)


@addr18list.handle()
async def _(arg: Message = CommandArg()):
    # 获取消息文本
    msg = arg.extract_plain_text().strip().split()[0]
    # 如果不是数字就返回
    if not msg.isdigit():
        await addr18list.finish("ID:"+msg+"不是数字")
    # 如果已经存在就返回
    if msg in r18list:
        await addr18list.finish("ID:"+msg+"已存在")
    r18list.append(msg)
    # 写入文件
    config_json.update({"r18list": r18list})
    write_configjson()
    await addr18list.finish("ID:"+msg+"添加成功")


# r18列表删除用的,权限SUPERSUSER
del_r18list = on_command(
    "del_r18", permission=SUPERUSER, block=True, priority=10)


@del_r18list.handle()
async def _(arg: Message = CommandArg()):
    # 获取消息文本
    msg = arg.extract_plain_text().strip()
    try:    
        r18list.remove(msg) 
    except ValueError:              # 如果不存在就返回
        await del_r18list.finish("ID:"+msg+"不存在")
    # 写入文件
    config_json.update({"r18list": r18list})    # 更新dict
    write_configjson()                        # 写入文件
    await del_r18list.finish("ID:"+msg+"删除成功")


get_r18list = on_command("r18名单", permission=SUPERUSER,
                         block=True, priority=10)

# 直接发送r18名单
@get_r18list.handle()
async def _():
    await get_r18list.finish("R18名单：\n" + str(r18list))


# 输出帮助信息
setu_help = on_command(
    "setu_help", block=True, priority=9)


@setu_help.handle()
async def _():
    reply = """命令头: setu|色图|涩图|想色色|来份色色|来份色图|想涩涩|多来点|来点色图|来张setu|来张色图|来点色色|色色|涩涩  (任意一个)
参数可接r18, 数量, 关键词
eg:         
setu 10张 r18 白丝
setu 10张 白丝
setu r18 白丝        
setu 白丝        
setu
(空格可去掉, 多tag用空格分开 eg:setu 白丝 loli)

superuser指令:
r18名单: 查看r18有哪些群聊或者账号
add_r18 xxx: 添加r18用户/群聊
del_r18 xxx: 移除r18用户
disactivate | 解除禁用 xxx: 恢复该群的setu功能
ban_setu xxx: 禁用xxx群聊的色图权限
setu_proxy: 更换setu代理(会提示一些允许可用的代理)

群主/管理员:
ban_setu: 禁用当前群聊功能, 解除需要找superuser"""
    await setu_help.finish(reply)   # 发送

admin_ban_setu = on_command("ban_setu", aliases={
                            "setu_ban", "禁用色图"}, permission=GROUP_OWNER | GROUP_ADMIN, priority=9, block=True)


@admin_ban_setu.handle()
async def _(event: GroupMessageEvent):
    gid: str = str(event.group_id)
    # 如果存在
    if gid in banlist:
        await admin_ban_setu.finish("ID:"+gid+"已存在")
    banlist.append(gid)
    config_json.update({"banlist": banlist})        # 更新dict
    write_configjson()                              # 写入文件
    await admin_ban_setu.finish("ID:"+gid+"禁用成功, 恢复需要找superuser")

su_ban_setu = on_command("ban_setu", aliases={
                         "setu_ban", "禁用色图"}, permission=SUPERUSER, priority=8, block=True)


@su_ban_setu.handle()
async def _(arg: Message = CommandArg()):
    # 获取消息文本
    msg = arg.extract_plain_text().strip()
    if not msg.isdigit():
        await su_ban_setu.finish("ID:"+msg+"不是数字")
    # 如果已经存在就返回
    if msg in banlist:
        await su_ban_setu.finish("ID:"+msg+"已存在")
    banlist.append(msg)            # 添加到list
    config_json.update({"banlist": banlist})    # 更新dict
    write_configjson()              # 写入文件
    await disactivate.finish("ID:"+msg+"禁用成功")


disactivate = on_command("disactivate", aliases={
                         "解除禁用"}, permission=SUPERUSER, priority=9, block=True)


@disactivate.handle()
async def _(arg: Message = CommandArg()):
    # 获取消息文本
    msg = arg.extract_plain_text().strip()
    try:
        banlist.remove(msg) # 如果不存在就直接finish
    except ValueError:
        await disactivate.finish("ID:"+msg+"不存在")
    config_json.update({"banlist": banlist})    # 更新dict 
    write_configjson()                # 写入文件
    await disactivate.finish("ID:"+msg+"解除成功")


# --------------- 更换代理 ---------------
replaceProxy = on_command(
    "更换代理", aliases={"替换代理", "setu_proxy"}, permission=SUPERUSER, block=True, priority=9)


@replaceProxy.handle()
async def _(matcher: Matcher, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()  # 获取消息文本
    if msg:
        matcher.set_arg("proxy", arg)   # 设置参数


@replaceProxy.got("proxy", prompt=f"请输入你要替换的proxy, 当前proxy为:{ReadProxy()}\ntips: 一些也许可用的proxy\ni.pixiv.re\nsex.nyan.xyz\npx2.rainchan.win\npximg.moonchan.xyz\npiv.deception.world\npx3.rainchan.win\npx.s.rainchan.win\npixiv.yuki.sh\npixiv.kagarise.workers.dev\npixiv.a-f.workers.dev\n等等....\n\neg:px2.rainchan.win\n警告:不要尝试命令行注入其他花里胡哨的东西, 可能会损伤你的电脑")
async def _(proxy: str = ArgPlainText("proxy")):
    setu_proxy = proxy.strip()  # 去除空格
    WriteProxy(setu_proxy)  # 写入proxy
    await replaceProxy.send(f"{proxy}已经替换, 正在尝试ping操作验证连通性") # 发送消息
    # 警告: 这部分带了一个ping代理服务器的操作, 这个响应器是superuser only, 用了os.popen().read()操作, 请不要尝试给自己电脑注入指令
    # 不会真的有弱智会这么做吧
    plat = platform.system().lower()    # 获取系统
    if plat == 'windows':
        result = os.popen(f"ping {setu_proxy}").read()  # windows下的ping
    elif plat == 'linux':   
        result = os.popen(f"ping -c 4 {setu_proxy}").read() # linux下的ping
    await replaceProxy.send(f"{result}\n如果丢失的数据比较多, 请考虑重新更换代理")  # 发送消息
