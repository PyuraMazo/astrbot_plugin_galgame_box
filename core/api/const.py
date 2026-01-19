
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
    'vn_of_producer': 'id,alttitle,title,released,rating,image{url}',
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
    'random': 'template3.html'
}

gender = {
    'm': '男性',
    'f': '女性',
    'b': '双性',
    'n': '无性'
}