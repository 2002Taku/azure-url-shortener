from flask import Flask, request, redirect, jsonify
from azure.cosmos import CosmosClient, exceptions
import string
import random
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 環境変数からCosmos DBの設定を取得
COSMOS_URI = os.getenv('COSMOS_URI')
COSMOS_KEY = os.getenv('COSMOS_KEY')
COSMOS_DATABASE = os.getenv('COSMOS_DATABASE')
COSMOS_CONTAINER = os.getenv('COSMOS_CONTAINER')

# Cosmos DBクライアントの初期化
client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = client.get_database_client(COSMOS_DATABASE)
container = database.get_container_client(COSMOS_CONTAINER)

# 短縮キーの生成
def generate_short_key(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        short_key = ''.join(random.choice(characters) for _ in range(length))
        # 短縮キーが既に存在しないか確認
        try:
            container.read_item(item=short_key, partition_key=short_key)
        except exceptions.CosmosResourceNotFoundError:
            return short_key

@app.route('/shorten', methods=['POST'])
def shorten_url():
    # リクエストのコンテンツタイプを確認
    if request.is_json:
        data = request.get_json()
        long_url = data.get('url')
    else:
        # フォームデータを取得
        long_url = request.form.get('url')

    if not long_url:
        # JSONリクエストの場合
        if request.is_json:
            return jsonify({'error': 'URLが提供されていません。'}), 400
        else:
            # フォームリクエストの場合
            return '''
                <h1>Error</h1>
                <p>URLが提供されていません。</p>
                <a href="/">ホームに戻る</a>
            ''', 400

    short_key = generate_short_key()
    short_url = request.host_url + short_key

    # Cosmos DBにマッピングを保存
    container.upsert_item({
        'id': short_key,
        'shortKey': short_key,
        'longUrl': long_url
    })

    # JSONリクエストの場合
    if request.is_json:
        return jsonify({'shortUrl': short_url}), 201
    else:
        # フォームリクエストの場合
        return f'''
            <h1>URLが短縮されました</h1>
            <p>短縮URL: <a href="{short_url}">{short_url}</a></p>
            <a href="/">他のURLを短縮する</a>
        ''', 201

@app.route('/<short_key>', methods=['GET'])
def redirect_url(short_key):
    try:
        item = container.read_item(item=short_key, partition_key=short_key)
        return redirect(item['longUrl'], code=302)
    except exceptions.CosmosResourceNotFoundError:
        return '''
            <h1>Error</h1>
            <p>URLが見つかりません。</p>
            <a href="/">ホームに戻る</a>
        ''', 404

@app.route('/', methods=['GET'])
def home():
    return '''
        <h1>Azure URL Shortener</h1>
        <form method="POST" action="/shorten">
            <input type="text" name="url" placeholder="Enter your URL here" size="50">
            <input type="submit" value="Shorten">
        </form>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
