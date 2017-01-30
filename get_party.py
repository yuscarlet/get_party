#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import bs4
import sys
import codecs
import requests
import unicodedata
import urllib.request
from readability import Document
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

# アイテムの表記ゆれ修正
def item_normalize(s):
    lst = s.split("@")
    pokemon_name = lst[0]
    target = lst[1]
    item_name = ""
    for item in item_list:
        if target.startswith(item[0]) :
            item_name = item[1]
    return pokemon_name+'@'+item_name

# テキストベースでの検索
def search_text(text, s):
    tmp = []
    last_idx = 0
    while True :
        item_idx_min = -1
        item_name_min = ""
        for item in item_list :
            idx = text.find(s+item[0], last_idx)
            if idx != -1 and (item_idx_min == -1 or item_idx_min > idx) :
                item_idx_min = idx
                item_name_min = item[0]
        if item_idx_min == -1:
            break

        pokemon_idx_max = -1
        pokemon_name_max = ""
        for pokemon in pokemon_list:
            idx = text.rfind(pokemon, 0, item_idx_min)
            if idx != -1 and (pokemon_idx_max == -1 or pokemon_idx_max < idx + len(pokemon)) :
                pokemon_idx_max = idx + len(pokemon)
                pokemon_name_max = pokemon
        if pokemon_idx_max == -1:
            break
        if not s == " " or item_idx_min - pokemon_idx_max <= 30: # 30 is magic number
            tmp.append(item_normalize(pokemon_name_max+'@'+item_name_min))
        last_idx = item_idx_min+len(item_name_min)
    res = list(set(tmp))
    return res

# 表を検索して読む
def search_table(text):
    tmp = []
    base_idx = 0
    last_idx = 0
    while True :
        idx = text.find("<tr>", last_idx)
        if idx == -1:
            break
        base_idx = idx + 1
        idx = text.find("</tr>", base_idx)
        if idx == -1:
            break
        last_idx = idx+1
        pokemon_name = ""
        item_name = ""
        item_idx = 0
        for item in item_list:
            idx = text.find(item[0], base_idx, last_idx)
            if idx != -1:
                item_name = item[1]
                item_idx = idx
        for pokemon in pokemon_list:
            idx = text.find(pokemon, base_idx, item_idx)
            if idx != -1:
                pokemon_name = pokemon
                break
        if pokemon_name != "" and item_name != "":
            tmp.append(item_normalize(pokemon_name+"@"+item_name))

    res = list(set(tmp))
    return res

# 画像を判定して云々（未実装）
def guess_from_image(url):
    headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'
    }

    request = "https://www.google.co.jp/searchbyimage?image_url=%s&lr=lang_ja" % url
    html = requests.get(request, headers=headers).text

    res = ""
    cnt = 0
    for pokemon in open('pokemon_list.txt', 'r'):
        pokemon = pokemon.replace('\n', '')
        tmp = html.count(pokemon)
        if tmp > cnt:
            res = pokemon
            cnt = tmp

    request = "https://www.google.co.jp/searchbyimage?image_url=%s" % url
    html = requests.get(request, headers=headers).text

    for pokemon in open('pokemon_list.txt', 'r'):
        pokemon = pokemon.replace('\n', '')
        tmp = html.count(pokemon)
        if tmp > cnt:
            res = pokemon
            cnt = tmp

    for pokemon in open('pokemon_list_en.txt', 'r'):
        names = pokemon.replace('\n', '').split(',')
        pokemon = names[1]
        tmp = html.count(pokemon)
        if tmp > cnt:
            res = names[0]
            cnt = tmp

    return (res)

if __name__ == '__main__':
    args = sys.argv
    url = args[1]
    print (url)
    cand_list = []

    # リストの読み込み
    item_list = []
    pokemon_list = []
    pokemon_replace_list = []
    for line in open('item_list.txt', 'r'):
        item_list.append(line.replace('\n','').split(","))
    for line in open('pokemon_list.txt', 'r'):
        pokemon_list.append(line.replace('\n',''))
    for line in open('pokemon_replace.txt', 'r'):
        pokemon_replace_list.append(line.replace('\n','').split(","))

    try:
        soup = bs4.BeautifulSoup(urllib.request.urlopen(url).read(), 'lxml')
    except:
        print ("request error!")
        sys.exit()

    # とりあえず正規化
    text = unicodedata.normalize('NFKC', str(soup))

    # 表形式の検索
    party = search_table(text)
    if len(party) >= 6 :
        print (len(party))
        for pokemon in party:
            print (pokemon, end=' ')
        print ("")
        sys.exit()
    else :
        cand_list.extend(party)

    # タグを消して試してみる
    text2 = strip_tags(text)

    # テキストベースでの検索
    test_list = ["@", u"持ち物:", u"持ち物 ", u"持ち物", "/", u"【", " ", u"...", u"・", u"・・・"]
    for s in test_list :
        party = search_text(text2, s)
        if len(party) >= 6 :
            print (len(party))
            for pokemon in party:
                print (pokemon, end=' ')
            print ("")
            sys.exit()
        else :
            cand_list.extend(party)

    for s in test_list :
        party = search_text(text, s)
        if len(party) >= 6 :
            print (len(party))
            for pokemon in party:
                print (pokemon, end='')
            print ("")
            sys.exit()
        else :
            cand_list.extend(party)

    # パーティに含まれる可能性のあるポケモンがいれば出力
    cand_list_uniq = list(set(cand_list))
    if len(cand_list_uniq) >= 1:
        print (str(len(cand_list_uniq)) + "?")
        for pokemon in cand_list_uniq:
            print (pokemon, end=' ')
        print ("")
        sys.exit()

    # @持ち物の前に画像があるパターンの検索
    # 未実装

    print ("Not found!")

