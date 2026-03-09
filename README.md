### Описание API
Сервис по генерации коротких ссылок.

Локальный адрес: http://127.0.0.1:8000

Методы DELETE и PUT доступны только авторизованным пользователям

### Примеры запросов:

#### Регистрация (/sign_up)
- Через Swagger UI (http://127.0.0.1:8000)
- Через командную строку: 
```bash
curl -X POST "http://127.0.0.1:8000/sign_up" -H "Content-Type: application/json" -d "{\"login\": \"user\", \"password\": \"password\"}"
```

#### POST /links/shorten
- Через Swagger UI (http://127.0.0.1:8000)
- Через командную строку:
```bash
curl -X POST "http://127.0.0.1:8000/links/shorten" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"long_url\": \"https://kaggle.com\", \"custom_alias\": \"kgl3\", \"expires_at\": \"2026-03-10T21:19:00\", \"login\": \"user\", \"password\": \"qwerty\"}"
```
Ненужные опциональные поля (все, кроме long_url) можно удалить из JSON.

#### GET /links/{short_code}
- Через Swagger UI (http://127.0.0.1:8000)
- В строке браузера: http://127.0.0.1:8000/links/QFdNIzU
- Через командную строку:
```bash
curl -X GET "http://127.0.0.1:8000/links/QFdNIzU" -H "accept: application/json"
```

#### DELETE /links/{short_code}
- Через Swagger UI (http://127.0.0.1:8000)
- Через командную строку:
```bash
curl -X DELETE "http://127.0.0.1:8000/links/kgl3" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"login\": \"user\", \"password\": \"qwerty\"}"
```

#### PUT /links/{short_code}
- Через Swagger UI (http://127.0.0.1:8000)
- Через командную строку:
```bash
curl -X PUT "http://127.0.0.1:8000/links/hNeyORR" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"login\": \"user\", \"password\": \"qwerty\"}"
```

#### GET /links/{short_code}/stats
- Через Swagger UI (http://127.0.0.1:8000)
- Через командную строку:
```bash
curl -X GET "http://127.0.0.1:8000/links/At9pmSx/stats" -H "accept: application/json"
```

#### GET /links/search
- Через Swagger UI (http://127.0.0.1:8000)
- Через командную строку:
```bash
curl -X GET "http://127.0.0.1:8000/links/search?original_url=https%3A%2F%2Fkaggle.com" -H "accept: application/json"
```

#### Дополнительная функция GET /links/expired (показ информации об истёкших ссылках)
- Через Swagger UI (http://127.0.0.1:8000)
- Через командную строку:
```bash
curl -X GET "http://127.0.0.1:8000/links/expired" -H "accept: application/json"
```

### Описание БД
Сервис использует PostgreSQL и SQLAlchemy. Есть 3 основных таблицы:
- links (содержит данные о ссылках: id, длинный адрес, короткий адрес, дату и время создания, количество кликов, дату и время последнего клика, дату и время окончания действия ссылки, id владельца)
- users (содержит данные о пользователях: id, логин, пароль)
- expired_links (содержит данные об истёкших ссылках: id, длинный адрес, короткий адрес, дату и время создания, количество кликов, дату и время последнего клика, дату и время окончания действия ссылки, id владельца)