
MIME_TYPE = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'avif': 'image/avif',
    'ttf': 'font/ttf'
}

vndb_command_fields = {
    'vn': 'id,average,rating,released,length_minutes,platforms,aliases,developers{id,original,name},titles{lang,title,official},image{url},alttitle,title',
    'character': 'id,name,aliases,sex,birthday,waist,hips,bust,blood_type,weight,height,cup,original,image{url},vns{id,alttitle,title}',
    'producer': 'id,name,original,aliases,lang,type',
    'vn_short': 'id,alttitle,title,released,rating,image{url}',
    'character_short': 'id,name,original,aliases,image{url},vns{id,alttitle,title}',
    'release': 'id,alttitle,title,extlinks{id,label},vns{id,image{url}}'
}

id2command = {
    'v': 'vn',
    'c': 'character',
    'p': 'producer'
}

lang = {
    'ja': '日文',
    'en': '英文',
    'zh-Hans': '简中',
    'zh-Hant': '繁中',
    'zh': '中文'
}

develop_type = {
    'co': '公司',
    'in': '个人',
    'ng': '业余团体'
}

html_list = {
    'vn': 'template1.html',
    'character': 'template1.html',
    'producer': 'template2.html',
    'random': 'template3.html',
    'find': 'template4.html',
    'recommend': 'template3.html',
    'schedule': 'template5.html'
}

gender = {
    'm': '男性',
    'f': '女性',
    'b': '双性',
    'n': '无性'
}

trace_code = {
    17701: '图片大小过大',
    17702: '服务器繁忙，请重试',
    17704: 'API维护中',
    17722: '图片下载失败',
    17728: '已达到本次使用上限'
}