from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from string import ascii_letters, digits
import random
from sqlalchemy.orm import Session
from database import engine, Link, User, ExpiredLink
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
from upstash_redis import Redis
import json
from typing import Optional
import os
from dotenv import load_dotenv


load_dotenv()


redis = Redis(url=os.getenv('REDIS_URL'), token=os.getenv('REDIS_TOKEN'))

app = FastAPI()


def delete_expired_links():
    with Session(engine) as db:
        expired_links = db.query(Link).filter(Link.expires_at <= datetime.now(timezone.utc)).all()
        if not expired_links:
            return
        for exp_link in expired_links:
            expired_link = ExpiredLink(
                long_url=exp_link.long_url,
                short_url=exp_link.short_url,
                create_dttm=exp_link.create_dttm,
                clicks_num=exp_link.clicks_num,
                last_click_dttm=exp_link.last_click_dttm,
                expired_at=exp_link.expires_at,
                owner_id=exp_link.owner_id
            )
            db.add(expired_link)
            redis.delete(f'search:{exp_link.long_url}')
            redis.delete(f'stats:{exp_link.short_url}')
            db.delete(exp_link)
        db.commit()


@app.post('/sign_up')
def sign_up(login: str = Body(), password: str = Body()):
    with Session(engine) as db:
        all_logins = set([row[0] for row in db.query(User.login).all()])
        if login in all_logins:
            raise HTTPException(status_code=409, detail='Этот логин уже используется. Попробуйте ещё раз.')
        new_user = User(login=login, password=password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        redis.setex(f'login:{new_user.login}', 1200, new_user.id)

        return {'id': new_user.id, 'login': new_user.login, 'message': 'Вы успешно зарегистрировались.'}
    

@app.get('/links/expired')
async def view_expired_links_info(background_tasks: BackgroundTasks):
    background_tasks.add_task(delete_expired_links)
    with Session(engine) as db:
        return db.query(ExpiredLink).all()


@app.get('/links/search')
async def find_short_link(original_url: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(delete_expired_links)
    cached = redis.get(f'search:{original_url}')
    if cached is not None:
        return {'long_url': original_url, 'short_url(-s)': json.loads(cached), 'source': 'cache'}
    with Session(engine) as db:
        row = db.query(Link.short_url).filter(Link.long_url == original_url).all()
        if not row:
            raise HTTPException(status_code=404, detail='Введённая длинная ссылка не найдена. Попробуйте ещё раз.')
        short_urls = [i[0] for i in row]
        redis.setex(f'search:{original_url}', 1200, short_urls)

        return {'long_url': original_url, 'short_url(-s)': short_urls, 'source': 'db'}
    

@app.post('/links/shorten')
async def shorten_link(
        background_tasks: BackgroundTasks,
        long_url: str = Body(), 
        custom_alias: Optional[str] = Body(None), 
        expires_at: Optional[datetime] = Body(None), 
        login: Optional[str] = Body(None),
        password: Optional[str] = Body(None)
    ):
    background_tasks.add_task(delete_expired_links)
    with Session(engine) as db:
        if login and password:
            owner_login = db.query(User).filter((User.login == login) & (User.password == password)).first()
            if not owner_login:
                raise HTTPException(status_code=401, detail='Введён неверный логин/пароль. Попробуйте ещё раз либо не указывайте логин и пароль.')
        all_short_urls = set([row[0] for row in db.query(Link.short_url).all()])
        if custom_alias:
            short_url = custom_alias
            if short_url in all_short_urls:
                raise HTTPException(status_code=409, detail='Короткая ссылка с введённым алиасом уже существует. Попробуйте ещё раз.')
        else:
            short_url = ''.join(random.choices(ascii_letters + digits, k=7))
            while short_url in all_short_urls:
                short_url = ''.join(random.choices(ascii_letters + digits, k=7))
        if login and password and owner_login:
            new_link = Link(long_url=long_url, short_url=short_url, create_dttm=datetime.now(timezone.utc), expires_at=expires_at, owner_id=owner_login.id)
        else:
            new_link = Link(long_url=long_url, short_url=short_url, create_dttm=datetime.now(timezone.utc), expires_at=expires_at)
        db.add(new_link)
        db.commit()

        return {'short_url': short_url, 'long_url': long_url, 'message': 'Короткая ссылка успешно создана'}


@app.get('/links/{short_code}')
async def redirect_to_original_url(short_code: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(delete_expired_links)
    with Session(engine) as db:
        row = db.query(Link).filter(Link.short_url == short_code).first()
        if not row:
            raise HTTPException(status_code=404, detail='Введённая короткая ссылка не найдена. Попробуйте ещё раз.')
        row.clicks_num += 1
        row.last_click_dttm = datetime.now(timezone.utc)
        db.commit()

        return RedirectResponse(row.long_url)


@app.delete('/links/{short_code}')
async def delete_connection_between_urls(
        background_tasks: BackgroundTasks,
        short_code: str,
        login: Optional[str] = Body(None),
        password: Optional[str] = Body(None)
    ):
    background_tasks.add_task(delete_expired_links)
    with Session(engine) as db:
        if login is None or password is None:
            raise HTTPException(status_code=401, detail='Вы не указали свой логин и/или пароль. Попробуйте ещё раз.')
        else:
            owner_login = db.query(User).filter((User.login == login) & (User.password == password)).first()
            if not owner_login:
                raise HTTPException(status_code=401, detail='Введён неверный логин/пароль. Пожалуйста, попробуйте ещё раз.')
            cached = redis.get(f'login:{login}')
            if cached is not None:
                owner_id = cached
            else:
                owner_id = db.query(User).filter(User.login == login).first()
            if not isinstance(owner_id, str):
                owner_id = owner_id.id
        row = db.query(Link).filter(Link.short_url == short_code).first()
        if not row:
            raise HTTPException(status_code=404, detail='Введённая короткая ссылка не найдена. Попробуйте ещё раз.')
        if not str(row.owner_id) == str(owner_id):
            raise HTTPException(status_code=403, detail='Недостаточно прав. Вы не являетесь владельцем короткой ссылки.')
        short_url = row.short_url
        long_url = row.long_url
        db.delete(row)
        db.commit()
        redis.delete(f'stats:{short_code}')
        redis.delete(f'search:{long_url}')

        return {'short_url': short_url, 'long_url': long_url, 'message': 'Связь между ссылками успешно удалена'}


@app.put('/links/{short_code}')
async def change_short_url(
        background_tasks: BackgroundTasks,
        short_code: str,
        login: Optional[str] = Body(None),
        password: Optional[str] = Body(None)
    ):
    background_tasks.add_task(delete_expired_links)
    with Session(engine) as db:
        if login is None or password is None:
            raise HTTPException(status_code=401, detail='Вы не указали свой логин и/или пароль. Попробуйте ещё раз.')
        else:
            owner_login = db.query(User).filter((User.login == login) & (User.password == password)).first()
            if not owner_login:
                raise HTTPException(status_code=401, detail='Введён неверный логин/пароль. Пожалуйста, попробуйте ещё раз.')
            cached = redis.get(f'login:{login}')
            if cached is not None:
                owner_id = cached
            else:
                owner_id = db.query(User).filter(User.login == login).first()
            if not owner_id:
                raise HTTPException(status_code=401, detail='Введённый логин не зарегистрирован. Пожалуйста, пройдите регистрацию.')
            if not isinstance(owner_id, str):
                owner_id = owner_id.id
        row = db.query(Link).filter(Link.short_url == short_code).first()
        if not row:
            raise HTTPException(status_code=404, detail='Введённая короткая ссылка не найдена. Попробуйте ещё раз.')
        if not str(row.owner_id) == str(owner_id):
            raise HTTPException(status_code=403, detail='Недостаточно прав. Вы не являетесь владельцем короткой ссылки.')
        old_short_url = row.short_url
        all_short_urls = set([row[0] for row in db.query(Link.short_url).all()])
        new_short_url = ''.join(random.choices(ascii_letters + digits, k=7))
        while new_short_url in all_short_urls:
            new_short_url = ''.join(random.choices(ascii_letters + digits, k=7))
        row.short_url = new_short_url
        long_url = row.long_url
        row.create_dttm = datetime.now(timezone.utc)
        db.commit()
        redis.delete(f'stats:{short_code}')
        redis.delete(f'search:{long_url}')

        return {'old_short_url': old_short_url, 'new_short_url': new_short_url, 'long_url': long_url, 'message': 'Короткая ссылка успешно обновлена'}


@app.get('/links/{short_code}/stats')
async def get_url_stats(short_code: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(delete_expired_links)
    cached = redis.get(f'stats:{short_code}')
    if cached is not None:
        cached = json.loads(cached)
        return {
            'long_url': cached['long_url'], 
            'short_url': cached['short_url'], 
            'short_url_creation_dt': cached['short_url_creation_dt'], 
            'clicks_num': cached['clicks_num'],
            'last_click_dt': cached['last_click_dt'],
            'source': 'cache'
        }
    with Session(engine) as db:
        row = db.query(Link).filter(Link.short_url == short_code).first()
        if not row:
            raise HTTPException(status_code=404, detail='Введённая короткая ссылка не найдена. Попробуйте ещё раз.')
        data = {
            'long_url': row.long_url,
            'short_url': row.short_url, 
            'short_url_creation_dt': str(row.create_dttm.date()), 
            'clicks_num': row.clicks_num,
            'last_click_dt': str(row.last_click_dttm.date()) if row.last_click_dttm else row.last_click_dttm,
        }
        redis.setex(f'stats:{short_code}', 1200, json.dumps(data))
        data['source'] = 'db'
        
        return data
