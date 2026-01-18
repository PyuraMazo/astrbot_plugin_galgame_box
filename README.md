# astrbot_plugin_galgame_tools
## 简介
[AstrBot](https://github.com/Soulter/AstrBot)的社区插件，结合了VNDB和TouchGal的API，不但能够提供全面、细节的Galgame帮助信息，还能提供TouchGal的随机作品和资源下载等功能。后续会结合更多Gal网站的API提供更有趣的功能。

## 使用
本插件以`gt`（别名`旮旯`）作为主指令，加空格调用子指令。
指令如下：

### 通过VNDB查找作品
- `/旮旯 作品 <作品名>`
### 通过VNDB查找角色
- `/旮旯 角色 <角色名>`
### 通过VNDB查找厂商
- `/旮旯 厂商 <厂商名>`
### 通过VNDB ID查询
- `/旮旯 ID <VNDB ID>`
### 通过TouchGal随机获取一部作品
- `/旮旯 随机`
### 通过TouchGal获取下载资源
- `/旮旯 下载 <内容>`

此处`<内容>`参数可以是TouchGal的纯数字ID，也可以是VNDB ID。当不符合上述两者时，会通过TouchGal搜索`<内容>`，如果有结果，就会让发送者进行选择。

---

#### 子指令都有各自的别名，此处并未展示

## 反馈

如果你遇到任何问题或者有任何改进建议，请通过以下方式联系我：  
-  邮箱：pyuramazo@vip.qq.com