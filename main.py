from aiohttp import web
import aiosqlite
from datetime import datetime

app = web.Application()

# Подключение к базе данных SQLite
async def get_db_connection():
    conn = await aiosqlite.connect('ads.db')
    conn.row_factory = aiosqlite.Row
    return conn

# Создание таблицы объявлений, если она не существует
async def init_db():
    conn = await get_db_connection()
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL,
            owner TEXT NOT NULL
        )
    ''')
    await conn.commit()
    await conn.close()

# Роут для создания объявления
async def create_ad(request):
    data = await request.json()
    title = data.get('title')
    description = data.get('description')
    owner = data.get('owner')

    if not title or not description or not owner:
        raise web.HTTPBadRequest(text='Title, description, and owner are required fields.')

    created_at = datetime.now().isoformat()

    conn = await get_db_connection()
    cursor = await conn.execute('''
        INSERT INTO ads (title, description, created_at, owner)
        VALUES (?, ?, ?, ?)
    ''', (title, description, created_at, owner))
    await conn.commit()
    ad_id = cursor.lastrowid
    await conn.close()

    return web.json_response({'id': ad_id, 'message': 'Ad created successfully'}, status=201)

# Роут для получения объявления по ID
async def get_ad(request):
    ad_id = int(request.match_info['ad_id'])
    conn = await get_db_connection()
    ad = await conn.execute('SELECT * FROM ads WHERE id = ?', (ad_id,))
    ad = await ad.fetchone()
    await conn.close()

    if ad is None:
        raise web.HTTPNotFound(text='Ad not found')

    return web.json_response({
        'id': ad['id'],
        'title': ad['title'],
        'description': ad['description'],
        'created_at': ad['created_at'],
        'owner': ad['owner']
    })

# Роут для удаления объявления по ID
async def delete_ad(request):
    ad_id = int(request.match_info['ad_id'])
    conn = await get_db_connection()
    result = await conn.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
    await conn.commit()
    await conn.close()

    if result.rowcount == 0:
        raise web.HTTPNotFound(text='Ad not found')

    return web.json_response({'message': 'Ad deleted successfully'}, status=200)

# Добавление роутов
app.router.add_post('/ads', create_ad)
app.router.add_get('/ads/{ad_id}', get_ad)
app.router.add_delete('/ads/{ad_id}', delete_ad)

# Обработка ошибок
async def handle_400(request, response):
    return web.json_response({'error': 'Bad Request', 'message': response.text}, status=400)

async def handle_404(request, response):
    return web.json_response({'error': 'Not Found', 'message': response.text}, status=404)

# Асинхронная лямбда-функция для обработки ошибок
async def error_middleware(app, handler):
    async def middleware_handler(request):
        try:
            response = await handler(request)
            if response.status == 400:
                return await handle_400(request, response)
            elif response.status == 404:
                return await handle_404(request, response)
            return response
        except web.HTTPBadRequest as e:
            return await handle_400(request, e)
        except web.HTTPNotFound as e:
            return await handle_404(request, e)
    return middleware_handler

app.middlewares.append(error_middleware)

async def main():
    await init_db()  # Инициализация базы данных перед запуском сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()
    print("Server started at http://127.0.0.1:8080")
    await asyncio.Event().wait()  # Бесконечный цикл ожидания

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())