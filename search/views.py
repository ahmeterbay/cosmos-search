from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
import json
import random
from random import shuffle
import re
import requests
from search.templatetags.calculator import getResult
from search.templatetags.youtube import youtube_search

COSMOS_SEP = '_'

# Create your views here


# To prefill the searchbar
def get_random_tag():
    jsonFile = open(settings.TAGS_JSON, 'r')
    algo_list = json.load(jsonFile)
    r_no = random.randint(0, len(algo_list) - 1)
    algo_tag = algo_list[r_no]
    return algo_tag


def searchSuggestion(request):
    jsonFile = open(settings.TAGS_JSON, 'r')
    algo_list = json.load(jsonFile)
    results = []
    if request.is_ajax():
        val = request.GET.get('term', '')
        filterData = []
        for word in algo_list:
            if word.startswith(val):
                filterData.append(word)
        i = 0
        for tag in filterData:
            tag_json = {}
            tag_json['id'] = filterData.index(tag)
            tag_json['label'] = tag
            tag_json['value'] = tag
            results.append(tag_json)
            i = i + 1
            if i >= 6:
                break
        searchTag = json.dumps(results)
    else:
        searchTag = 'fail'
    return searchTag


def index(request):
    algo_tag = get_random_tag()
    algo = searchSuggestion(request)
    if request.is_ajax():
        mimetype = 'application/json'
        return HttpResponse(algo, mimetype)
    return render(request, 'cosmos/index.html', {'algo_name': algo_tag})


# Handlers for error pages
def error400(request):
    return render(request, 'cosmos/error/HTTP400.html')


def error403(request):
    return render(request, 'cosmos/error/HTTP403.html')


def error404(request):
    return render(request, 'cosmos/error/HTTP404.html')


def error500(request):
    return render(request, 'cosmos/error/HTTP500.html')


# calculator
def calculator(request):
    global exprResult
    exprResult = 'ds'
    if request.method == 'POST':
        q = request.POST.get('txt')
        if q is not None:
            getResult(q)
            res = getResult(q)
            if type(res) == int or type(res) == float:
                exprResult = round(res, 3)
            else:
                exprResult = 'Error'
        else:
            return 'not expression'
    else:
        exprResult = None
        q = None
    return render(request, 'cosmos/searchresults.html',
                  {'title': 'Calculator',
                   'query': q,
                   'result_val': exprResult,
                   'active_tab': 'query',
                   'vid_amount': 0,
                   'amount': 0,
                   })


def is_file_extension_ignored(file_):
    return file_.split('.')[-1] in ['md', 'MD']


# Search query
ans = []
rec = []


def query(request):
    global ans, rec
    title = ''
    algo_name = ''
    amount = 0
    video_res = {}
    exprResult = None
    query = ''

    if request.is_ajax():
        data = request.GET.get('name', None)
        if data:
            video_res = video_search(request, data)
            res = {
                'videos': video_res['videos'],
                'next_page': video_res['next_page'],
                'vid_amount': video_res['amount']
            }
            video = json.dumps(res)
            mimetype = 'application/json'
            return HttpResponse(video, mimetype)
        else:
            algo = searchSuggestion(request)
            mimetype = 'application/json'
            return HttpResponse(algo, mimetype)

    if request.method == 'GET':
        ans = []
        rec = []
        query = re.escape(request.GET['q']).replace('\ ', ' ')

        if '\\' in query:
            query = query.replace('\\', '')

        query = query.lower()
        res = getResult(query)
        if type(res) == int or type(res) == float:
            exprResult = round(res, 3)
            title = "Calculator"
            algo_name = ""
        else:
            exprResult = None

        query = ' '.join(query.split())
        q = query.replace(' ', COSMOS_SEP)
        data = json.loads(open(settings.METADATA_JSON, 'r').readline())
        for folder, file in data.items():
            filtered_v = []
            for f in file:
                if not is_file_extension_ignored(f):
                    filtered_v.append(f)
            if q in folder and "test" not in folder.split("/"):
                if filtered_v:
                    path = folder
                    folder_list = folder.split('/')
                    ans.append({'path': path, 'dirs': folder_list, 'files': filtered_v})
                    amount += len(filtered_v)
                    if len(folder_list) == 2:
                        d = folder_list[-2] + '/'
                    else:
                        d = folder_list[-3] + '/'
                    for i, j in data.items():
                            if d in i:
                                if q not in i:
                                    only_contents_md = True
                                    for f in j:
                                        if not is_file_extension_ignored(f):
                                            only_contents_md = False
                                            break
                                    if only_contents_md:
                                        continue
                                    p = i
                                    p = p.split('/')
                                    l = p[len(p) - 1]
                                    rec.append({'recpath': i, 'recdirs': p, 'last': l})
        active = 'query'

        if not ans and exprResult is None:
            video_res = video_search(request, query)
            title = query

        elif ans:
            video_res = video_search(request, query)
            algo_name = query
            title = query
        else:
            video_res = {
                'videos': None,
                'next_page': None,
                'amount': 0
            }

        if ans and exprResult:
            amount += 1

        shuffle(rec)

    elif request.method == 'POST':
        calculator(request)
        active = 'query'

    if not ans and not exprResult and not video_res:
        return render(request, 'cosmos/notfound.html')

    return render(request, 'cosmos/searchresults.html',
                  {'amount': amount,
                   'title': title,
                   'result': ans,
                   'recommend': rec[:5],
                   'query': query,
                   'result_val': exprResult,
                   'algo_name': algo_name,
                   'videos': video_res['videos'],
                   'next_page': video_res['next_page'],
                   'vid_amount': video_res['amount'],
                   'active_tab': active
                   })


def video_search(request, term=None):
    youtube_result = {}
    query = ''

    if request.is_ajax():
        query = term
        q = query.split('&')
        if len(q[0].split(" ")) == 1:
            searchKey = q[0] + '+' + 'algorithm'
        else:
            searchKey = q[0].replace(' ', '+')
        youtube_query = {
            'q': searchKey,
            'max_results': 25,
            'next_page': q[1],
            'id': q[-1]
        }
        query = q[0]
        youtube_result = youtube_search(youtube_query)
    elif request.method == 'GET':
        query = term
        if len(query.split(" ")) == 1:
            searchKey = query + '+' + 'algorithm'
        else:
            searchKey = query.replace(' ', '+')

        youtube_query = {
            'q': searchKey,
            'max_results': 25,
            'next_page': '',
            'id': 0
        }
        youtube_result = youtube_search(youtube_query)

    res = {
        'amount': len(youtube_result['videos_Results']),
        'videos': youtube_result['videos_Results'],
        'title': 'Videos',
        'query': query,
        'next_page': youtube_result['nextpage'],
    }
    return res


# Search strategy
def subsq(a, b, m, n):
    # Base Cases
    if m == 0:
        return True
    if n == 0:
        return False
    # If last characters of two strings are matching
    if a[m - 1] == b[n - 1]:
        return subsq(a, b, m - 1, n - 1)
    # If last characters are not matching
    return subsq(a, b, m, n - 1)


def display(request):
    path = request.GET['path']
    display = "https://raw.githubusercontent.com/OpenGenus/cosmos/master/code/" + path
    r = requests.get(display)
    path = path.replace('_', ' ')
    path = path.replace('.', ' in ')
    l = path.split('/')
    if 'src' in l:
        l.remove('src')
    return render(request, 'cosmos/data.html', {'code': r.text, 'path': l})
