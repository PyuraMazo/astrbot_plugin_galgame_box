
# Galgame百宝盒
## 简介
[AstrBot](https://github.com/AstrBotDevs/AstrBot)的社区插件，本插件几乎满足了用户的所有与Gal相关的需求。结合了VNDB、Bangumi、TouchGal、AnimeTrace的API，
能够提供全面、贴心的Galgame帮助信息。本插件还配备了 **推荐作品** 、 **资源下载** 、 **角色识别** 、 **今日事件** 等功能以丰富Gal功能。

## 效果

### 查询厂商
![查询厂商](https://github.com/PyuraMazo/astrbot_plugin_galgame_box/blob/master/resources/preview/producer.jpg)

### 按要求推荐
![按要求推荐](https://github.com/PyuraMazo/astrbot_plugin_galgame_box/blob/master/resources/preview/recommend.jpg)

### Steam拼图（v2版本暂时移除）
![Steam拼图](https://github.com/PyuraMazo/astrbot_plugin_galgame_box/blob/master/resources/preview/puzzle.jpg)


## 使用指南

本插件以 **`旮旯`** 作为主指令，后接空格与子指令即可调用各项功能。

> 本插件几乎所有结果反馈都是以图片形式呈现，因此使用了AstrBot官方的渲染服务，此渲染服务默认渲染服务器的响应时间较长。如需缩短渲染时间以优化使用体验，请根据[官方部署教程](https://docs.astrbot.app/others/self-host-t2i.html)部署本地渲染服务。

##  功能列表

> 演示使用 **`/`** 作为唤醒符

> 你可以在UI界面根据需要设置指令别名。

###  VNDB 相关
| 功能    | 指令格式               | 别名               | 说明                        |
|-------|--------------------|------------------|---------------------------|
| 指令查询  | `/旮旯`              | `gal`、`GAL`      | 指令组，查询子指令信息               |
| 作品查询  | `/旮旯 作品 <作品名>`     | `游戏`、`vn`        | 搜索指定作品                    |
| 角色查询  | `/旮旯 角色 <角色名>`     | `人物`、`character` | 搜索指定角色                    |
| 厂商查询  | `/旮旯 厂商 <厂商名>`     | `作者`、`producer`  | 搜索指定厂商                    |
| 简讯获取  | `/旮旯 简讯 [指定日期]`    | `event `         | 获取指定日期发售游戏与生日角色的信息 |

**关于ID查询参数 `<VNDB ID>`：**
- 目前插件仅支持通过VNDB ID查询作品、角色和厂商
- 查询作品时会尝试从Bangumi获取简介；未匹配到Bangumi条目时仍可查询VNDB作品信息

**关于简讯获取参数 `[指定日期]`：**
- 可选。日期格式为MM-DD，不填则为本日

###  Bangumi 相关（需设置代理）
> 使用Bangumi相关指令之前，请务必在插件配置页设置代理地址。

| 功能 | 指令格式 | 别名 | 说明 |
|------|----------|------|------|
| ID 查询 | `/旮旯 ID <VNDB ID>` | `id`             | 通过 VNDB ID 直接查询           |
| 随机作品 | `/旮旯 随机` | `random` | 从VNDB随机抽取作品，并尝试获取对应的Bangumi简介 |


###  TouchGal 相关（逐步弃用）
> 推荐使用本插件的TouchGal功能前手动下载`curl_cffi`包，以帮助绕过该网站的CF拦截（因防护加强，因此逐步将功能向 **Bangumi** 迁移）。

> 你可以在`控制面板 > 平台日志 > 安装pip库`来实现简单安装。
> 
> 亦可在可控环境中通过命令`pip install curl_cffi`安装。

| 功能 | 指令格式 | 别名               | 说明       |
|------|----------|------------------|----------|
| 资源下载 | `/旮旯 下载 <内容>` | `资源`、`download`  | 获取游戏资源   |
| 推荐作品 | `/旮旯 推荐 <标签>` | `标签`、`recommend` | 通过标签搜索作品 |

**关于资源下载参数 `<内容>`：**
- 可以是 TouchGal 纯数字 ID
- 可以是 VNDB ID
- 其他情况下，将通过 TouchGal 搜索该内容并让用户选择结果

**关于推荐作品参数 `<标签>`：**
- 必填，否则请使用 **随机作品** 指令
- 标签可以是多个，多个标签请用 **空格** 分隔

###  AnimeTrace 相关
| 功能 | 指令格式        | 别名          |  说明 |
|------|-------------|-------------|----|
| 角色识别 | `/旮旯 出处 [图片链接]` | `识别`、`find` | 智能图像识别

**使用说明：**
- 如不填写参数，将开启会话等待用户发送图片
- **图片链接**只能在调用指令时参数传入，会话中不接受图片链接
- 支持引用一张图片进行识别

### 每日推送功能
会每天定时推送历史上今天发售的高分作品和今天过生日的高分角色。作品及角色基础信息来自VNDB；作品简介若能匹配到Bangumi条目，则优先使用Bangumi简介。
如果群发白名单为空，则不会启动此功能。

更多个性化推送请见插件的 **每日推送** 配置项。

**添加白名单**

白名单格式为 `平台id-群聊id` 

- 平台id: 在创建机器人实例时输入的 **机器人名称** 
- 群聊id: 当前平台的 **群聊号** 

## 反馈

如果你遇到任何问题或者有任何改进建议，请通过以下方式反馈：  
-  邮箱：pyuramazo@vip.qq.com
- Github： [Issues](https://github.com/PyuraMazo/astrbot_plugin_galgame_box/issues)

如果觉得插件不错，请在Github上为我点个Star！