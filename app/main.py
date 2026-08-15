# -*- coding: utf-8 -*-
import os
import re

import requests
from flask import Flask, Response, redirect, request
from requests.exceptions import (
    ChunkedEncodingError,
    ContentDecodingError, ConnectionError, StreamConsumedError)
from requests.utils import (
    stream_decode_response_unicode, iter_slices, CaseInsensitiveDict)
from urllib3.exceptions import (
    DecodeError, ReadTimeoutError, ProtocolError)
from urllib.parse import quote

# config
# 分支文件使用jsDelivr镜像的开关，0为关闭，默认关闭
ASSET_URL = os.getenv('GH_PROXY_ASSET_URL', 'https://zvonimirsun.github.io/gh-proxy/')
PREFIX = os.getenv('GH_PROXY_PREFIX', '/')
jsdelivr = os.getenv('GH_PROXY_JSDELIVR', '0') == '1'
# 逗号分隔的 URL 包含匹配，e.g. /user1/,/user2/
white_list = [item.strip() for item in os.getenv('GH_PROXY_WHITELIST', '').split(',') if item.strip()]
size_limit = 1024 * 1024 * 1024 * 999  # 允许的文件大小，默认999GB，相当于无限制了 https://github.com/hunshcn/gh-proxy/issues/8

"""
  先匹配 GH_PROXY_WHITELIST，再匹配黑名单，pass_list匹配到的会直接302到jsdelivr而忽略设置
  生效顺序 白->黑->pass，可以前往https://github.com/hunshcn/gh-proxy/issues/41 查看示例
  black_list和pass_list每个规则一行，可以匹配某个用户的所有仓库或特定仓库
  user1 # 封禁user1的所有仓库
  user1/repo1 # 封禁user1的repo1
  */repo1 # 封禁所有叫做repo1的仓库
"""
black_list = '''
'''
pass_list = '''
'''

HOST = '127.0.0.1'  # 监听地址，建议监听本地然后由web服务器反代
PORT = 80  # 监听端口

black_list = [tuple([x.replace(' ', '') for x in i.split('/')]) for i in black_list.split('\n') if i]
pass_list = [tuple([x.replace(' ', '') for x in i.split('/')]) for i in pass_list.split('\n') if i]
app = Flask(__name__)
CHUNK_SIZE = 1024 * 10
index_html = requests.get(ASSET_URL, timeout=10).text
icon_r = requests.get(ASSET_URL + 'favicon.ico', timeout=10).content
exp1 = re.compile(r'^(?:https?://)?github\.com/(?P<author>.+?)/(?P<repo>.+?)/(?:releases|archive)/.*$')
exp2 = re.compile(r'^(?:https?://)?github\.com/(?P<author>.+?)/(?P<repo>.+?)/(?:blob|raw)/.*$')
exp3 = re.compile(r'^(?:https?://)?github\.com/(?P<author>.+?)/(?P<repo>.+?)/(?:info|git-).*$')
exp4 = re.compile(r'^(?:https?://)?raw\.(?:githubusercontent|github)\.com/(?P<author>.+?)/(?P<repo>.+?)/.+?/.+$')
exp5 = re.compile(r'^(?:https?://)?gist\.(?:githubusercontent|github)\.com/(?P<author>.+?)/.+?/.+$')
exp6 = re.compile(r'^(?:https?://)?github\.com/(?P<author>.+?)/(?P<repo>.+?)/tags.*$')

requests.sessions.default_headers = lambda: CaseInsensitiveDict()


@app.route(PREFIX)
def index():
    if 'q' in request.args:
        return redirect(PREFIX + request.args.get('q'))
    return index_html


@app.route(PREFIX + 'favicon.ico')
def icon():
    return Response(icon_r, content_type='image/vnd.microsoft.icon')


def iter_content(self, chunk_size=1, decode_unicode=False):
    """rewrite requests function, set decode_content with False"""

    def generate():
        # Special case for urllib3.
        if hasattr(self.raw, 'stream'):
            try:
                for chunk in self.raw.stream(chunk_size, decode_content=False):
                    yield chunk
            except ProtocolError as e:
                raise ChunkedEncodingError(e)
            except DecodeError as e:
                raise ContentDecodingError(e)
            except ReadTimeoutError as e:
                raise ConnectionError(e)
        else:
            # Standard file-like object.
            while True:
                chunk = self.raw.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        self._content_consumed = True

    if self._content_consumed and isinstance(self._content, bool):
        raise StreamConsumedError()
    elif chunk_size is not None and not isinstance(chunk_size, int):
        raise TypeError("chunk_size must be an int, it is instead a %s." % type(chunk_size))
    # simulate reading small chunks of the content
    reused_chunks = iter_slices(self._content, chunk_size)

    stream_chunks = generate()

    chunks = reused_chunks if self._content_consumed else stream_chunks

    if decode_unicode:
        chunks = stream_decode_response_unicode(chunks, self)

    return chunks


def check_url(u):
    for exp in (exp1, exp2, exp3, exp4, exp5, exp6):
        m = exp.match(u)
        if m:
            return m
    return False


def check_white_list(u):
    if not white_list:
        return True

    repo_match = re.match(
        r'^(?:https?://)?(?:github\.com|raw\.(?:githubusercontent|github)\.com)/([^/]+)/([^/]+)',
        u,
        re.I) or re.match(
            r'^(?:https?://)?gist\.(?:githubusercontent|github)\.com/([^/]+)',
            u,
            re.I)
    for rule in white_list:
        # 保留 Worker 原有的 /user/ URL 包含匹配，同时兼容 Python 版仓库规则。
        if rule.startswith('/') or rule.endswith('/'):
            if rule in u:
                return True
            continue
        if not repo_match:
            continue

        parts = tuple(item.strip() for item in rule.split('/') if item.strip())
        repo_parts = repo_match.groups()
        if len(parts) == 1 and repo_parts[0] == parts[0]:
            return True
        if (len(parts) == 2 and
                len(repo_parts) == 2 and
                (parts[0] == '*' or repo_parts[0] == parts[0]) and
                repo_parts[1] == parts[1]):
            return True
    return False


@app.route(PREFIX + '<path:u>', methods=['GET', 'POST'])
def handler(u):
    # shorthand 和完整地址复用同一组正则，避免两套代理路径逐渐产生差异。
    has_github_host = re.match(r'^(?:github\.com|raw\.(?:githubusercontent|github)\.com|gist\.(?:githubusercontent|github)\.com)/', u, re.I)
    short_url = None if u.startswith('http') or has_github_host else 'https://github.com/' + u
    u = short_url if short_url and check_url(short_url) else (u if u.startswith('http') else 'https://' + u)
    if u.rfind('://', 3, 9) == -1:
        u = u.replace('s:/', 's://', 1)  # uwsgi会将//传递为/
    pass_by = False
    m = check_url(u)
    if m:
        m = tuple(m.groups())
        if not check_white_list(u):
            return Response('Forbidden by white list.', status=403)
        for i in black_list:
            if m[:len(i)] == i or i[0] == '*' and len(m) == 2 and m[1] == i[1]:
                return Response('Forbidden by black list.', status=403)
        for i in pass_list:
            if m[:len(i)] == i or i[0] == '*' and len(m) == 2 and m[1] == i[1]:
                pass_by = True
                break
    else:
        return Response('Invalid input.', status=403)

    if (jsdelivr or pass_by) and exp2.match(u):
        u = u.replace('/blob/', '@', 1).replace('github.com', 'cdn.jsdelivr.net/gh', 1)
        return redirect(u)
    elif (jsdelivr or pass_by) and exp4.match(u):
        u = re.sub(r'(\.com/.*?/.+?)/(.+?/)', r'\1@\2', u, 1)
        _u = u.replace('raw.githubusercontent.com', 'cdn.jsdelivr.net/gh', 1)
        u = u.replace('raw.github.com', 'cdn.jsdelivr.net/gh', 1) if _u == u else _u
        return redirect(u)
    else:
        if exp2.match(u):
            u = u.replace('/blob/', '/raw/', 1)
        if pass_by:
            url = u + request.url.replace(request.base_url, '', 1)
            if url.startswith('https:/') and not url.startswith('https://'):
                url = 'https://' + url[7:]
            return redirect(url)
        u = quote(u, safe='/:')
        return proxy(u)


def proxy(u, allow_redirects=False):
    headers = {}
    r_headers = dict(request.headers)
    if 'Host' in r_headers:
        r_headers.pop('Host')
    try:
        url = u + request.url.replace(request.base_url, '', 1)
        if url.startswith('https:/') and not url.startswith('https://'):
            url = 'https://' + url[7:]
        r = requests.request(method=request.method, url=url, data=request.data, headers=r_headers, stream=True, allow_redirects=allow_redirects)
        headers = dict(r.headers)

        if 'Content-length' in r.headers and int(r.headers['Content-length']) > size_limit:
            return redirect(u + request.url.replace(request.base_url, '', 1))

        def generate():
            for chunk in iter_content(r, chunk_size=CHUNK_SIZE):
                yield chunk

        if 'Location' in r.headers:
            _location = r.headers.get('Location')
            if check_url(_location):
                headers['Location'] = PREFIX + _location
            else:
                return proxy(_location, True)

        return Response(generate(), headers=headers, status=r.status_code)
    except Exception as e:
        headers['content-type'] = 'text/html; charset=UTF-8'
        return Response('server error ' + str(e), status=500, headers=headers)

app.debug = True
if __name__ == '__main__':
    app.run(host=HOST, port=PORT)
